from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.core.enums import EmailTokenKind
from app.main import app
from app.modules.auth import AuthService
from app.schemas import InvoiceListResponse, SubscriptionListResponse
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(client: AsyncClient, email: str) -> tuple[UUID, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Historial User"},
    )
    assert reg.status_code == 201
    user_id = UUID(reg.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    assert (await client.post("/api/v1/auth/verify", json={"token": token})).status_code == 200
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return user_id, login.json()["access_token"]


async def test_list_subscriptions_and_invoices_empty() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, "hist-empty@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}

        subs = await client.get("/api/v1/subscriptions", headers=headers)
        assert subs.status_code == 200
        body = subs.json()
        assert body["subscriptions"] == []
        assert body["next_cursor"] is None

        invoices = await client.get("/api/v1/invoices", headers=headers)
        assert invoices.status_code == 200
        body = invoices.json()
        assert body["invoices"] == []
        assert body["next_cursor"] is None


async def test_list_subscriptions_and_invoices_populated_owner_only() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        user_a, token_a = await _create_active_user(client, "hist-a@koicloud.dev")
        _, token_b = await _create_active_user(client, "hist-b@koicloud.dev")

        sub_a = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"plan_id": "micro"},
        )
        assert sub_a.status_code == 202
        invoice_a_id = sub_a.json()["invoice"]["id"]

        sub_b = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"plan_id": "micro"},
        )
        assert sub_b.status_code == 202

        listed = await client.get(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert listed.status_code == 200
        subs = listed.json()["subscriptions"]
        assert len(subs) == 1
        assert subs[0]["user_id"] == str(user_a)
        assert listed.json()["next_cursor"] is None

        invoices = await client.get(
            "/api/v1/invoices",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert invoices.status_code == 200
        rows = invoices.json()["invoices"]
        assert len(rows) == 1
        assert rows[0]["id"] == invoice_a_id
        assert rows[0]["user_id"] == str(user_a)
        assert invoices.json()["next_cursor"] is None


async def test_list_schemas_have_coherent_examples() -> None:
    sub_example = SubscriptionListResponse.example_data()
    assert "subscriptions" in sub_example
    assert "next_cursor" in sub_example
    assert isinstance(sub_example["subscriptions"], list)

    inv_example = InvoiceListResponse.example_data()
    assert "invoices" in inv_example
    assert "next_cursor" in inv_example
    assert isinstance(inv_example["invoices"], list)
