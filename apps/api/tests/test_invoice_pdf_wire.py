from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.core.enums import EmailTokenKind
from app.main import app
from app.modules.auth import AuthService
from app.modules.billing.invoice_pdf import ACADEMIC_FOOTER
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(client: AsyncClient, email: str) -> tuple[UUID, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "PDF User"},
    )
    assert reg.status_code == 201
    user_id = UUID(reg.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    assert (await client.post("/api/v1/auth/verify", json={"token": token})).status_code == 200
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return user_id, login.json()["access_token"]


async def test_get_invoice_pdf_renders_iva_pdf() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, "pdf-wire@koicloud.dev")
        subscribe = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_id": "micro"},
        )
        assert subscribe.status_code == 202
        invoice_id = subscribe.json()["invoice"]["id"]
        pdf = await client.get(
            f"/api/v1/invoices/{invoice_id}/pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        assert len(pdf.content) > 1024
        text = pdf.content.decode("latin-1", errors="ignore")
        assert "IVA" in text
        assert "12" in text
        assert ACADEMIC_FOOTER in text
        assert "KC-" in text


async def test_get_invoice_pdf_not_owner() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token_a = await _create_active_user(client, "pdf-owner@koicloud.dev")
        _, token_b = await _create_active_user(client, "pdf-other@koicloud.dev")
        subscribe = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"plan_id": "micro"},
        )
        assert subscribe.status_code == 202
        invoice_id = subscribe.json()["invoice"]["id"]
        http = await client.get(
            f"/api/v1/invoices/{invoice_id}/pdf",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert http.status_code == 403
        assert http.json()["code"] == "not_owner"
