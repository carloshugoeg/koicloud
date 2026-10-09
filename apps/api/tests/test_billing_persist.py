from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.enums import EmailTokenKind
from app.core.time import utc_now
from app.main import app
from app.modules.auth import AuthService
from app.modules.billing.invoice_pdf import split_iva
from app.modules.billing.payments import get_payment_provider
from app.modules.billing.payments.simulated import SimulatedPaymentProvider
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(client: AsyncClient, email: str) -> tuple[UUID, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Billing User"},
    )
    assert reg.status_code == 201
    user_id = UUID(reg.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    assert (await client.post("/api/v1/auth/verify", json={"token": token})).status_code == 200
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return user_id, login.json()["access_token"]


async def test_subscribe_persists_via_payment_port() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        user_id, token = await _create_active_user(client, "billing-persist@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}
        first = await client.post("/api/v1/subscriptions", headers=headers, json={"plan_id": "micro"})
        second = await client.post("/api/v1/subscriptions", headers=headers, json={"plan_id": "micro"})
        assert first.status_code == 202
        assert second.status_code == 202
        body = first.json()
        n1 = body["invoice"]["number"]
        n2 = second.json()["invoice"]["number"]
        year = utc_now().year
        assert n1 == f"KC-{year}-000001"
        assert n2 == f"KC-{year}-000002"
        assert body["subscription"]["user_id"] == str(user_id)
        assert body["subscription"]["status"] == "active"
        assert body["invoice"]["status"] == "paid"
        assert body["payment"]["status"] == "succeeded"
        assert body["payment"]["method"] == "simulated"
        subtotal, iva = split_iva(Decimal("5.0"))
        assert body["invoice"]["subtotal_usd"] == float(subtotal)
        assert body["invoice"]["iva_usd"] == float(iva)
        assert body["invoice"]["total_usd"] == 5.0

        listed = await client.get("/api/v1/invoices", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()["invoices"]) == 2

        pdf = await client.get(f"/api/v1/invoices/{body['invoice']['id']}/pdf", headers=headers)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")


async def test_concurrent_subscribe_unique_invoice_numbers() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        users = []
        for idx in range(3):
            users.append(
                await _create_active_user(client, f"billing-race-{idx}@koicloud.dev")
            )

        async def _subscribe(token: str):
            return await client.post(
                "/api/v1/subscriptions",
                headers={"Authorization": f"Bearer {token}"},
                json={"plan_id": "micro"},
            )

        responses = await asyncio.gather(*[_subscribe(token) for _, token in users])
        assert all(response.status_code == 202 for response in responses)
        numbers = [response.json()["invoice"]["number"] for response in responses]
        assert len(numbers) == len(set(numbers))
        year = utc_now().year
        assert all(number.startswith(f"KC-{year}-") for number in numbers)


def test_simulated_provider_factory_default() -> None:
    provider = get_payment_provider(get_settings())
    assert isinstance(provider, SimulatedPaymentProvider)
