from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from app.core.enums import EmailTokenKind
from app.main import app
from app.modules.auth import AuthService
from app.modules.billing.invoice_pdf import split_iva
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(client: AsyncClient, email: str) -> tuple[UUID, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Invoice User"},
    )
    assert reg.status_code == 201
    user_id = UUID(reg.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    assert (await client.post("/api/v1/auth/verify", json={"token": token})).status_code == 200
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return user_id, login.json()["access_token"]


async def _subscribe(client: AsyncClient, token: str) -> dict:
    response = await client.post(
        "/api/v1/subscriptions",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_id": "micro"},
    )
    assert response.status_code == 202
    return response.json()


async def test_invoice_detail_includes_lines_and_iva() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, "detail-owner@koicloud.dev")
        invoice_id = (await _subscribe(client, token))["invoice"]["id"]
        detail = await client.get(
            f"/api/v1/invoices/{invoice_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        body = detail.json()
        invoice = body["invoice"]
        subtotal, iva = split_iva(Decimal("5.0"))
        assert invoice["subtotal_usd"] == float(subtotal)
        assert invoice["iva_usd"] == float(iva)
        assert invoice["total_usd"] == 5.0
        assert len(body["lines"]) == 1
        assert body["lines"][0]["invoice_id"] == invoice_id
        assert body["lines"][0]["amount_usd"] == float(subtotal)


async def test_invoice_pdf_attachment_and_regenerate() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, "pdf-detail@koicloud.dev")
        invoice_id = (await _subscribe(client, token))["invoice"]["id"]
        headers = {"Authorization": f"Bearer {token}"}
        first = await client.get(f"/api/v1/invoices/{invoice_id}/pdf", headers=headers)
        assert first.status_code == 200
        assert first.headers["content-type"].startswith("application/pdf")
        assert first.headers["content-disposition"].startswith("attachment;")
        assert first.content.startswith(b"%PDF")

        detail = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
        pdf_path = Path(detail.json()["invoice"]["pdf_path"])
        assert pdf_path.is_file()
        pdf_path.unlink()
        assert not pdf_path.exists()

        second = await client.get(f"/api/v1/invoices/{invoice_id}/pdf", headers=headers)
        assert second.status_code == 200
        assert second.content.startswith(b"%PDF")
        assert pdf_path.is_file()


async def test_invoice_detail_and_pdf_not_owner() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token_a = await _create_active_user(client, "pdf-a@koicloud.dev")
        _, token_b = await _create_active_user(client, "pdf-b@koicloud.dev")
        invoice_id = (await _subscribe(client, token_a))["invoice"]["id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        detail = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers_b)
        assert detail.status_code == 403
        assert detail.json()["code"] == "not_owner"

        pdf = await client.get(f"/api/v1/invoices/{invoice_id}/pdf", headers=headers_b)
        assert pdf.status_code == 403
        assert pdf.json()["code"] == "not_owner"


async def test_invoice_detail_missing_is_404() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, "pdf-missing@koicloud.dev")
        missing = await client.get(
            f"/api/v1/invoices/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing.status_code == 404
        assert "code" in missing.json()


async def test_invoice_pdf_missing_is_404() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, "pdf-404@koicloud.dev")
        missing = await client.get(
            f"/api/v1/invoices/{uuid4()}/pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing.status_code == 404
        body = missing.json()
        assert body["code"] == "pond_not_found"
