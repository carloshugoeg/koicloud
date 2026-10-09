from __future__ import annotations

from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from app.commands import billing as billing_commands
from app.core.auth import AuthContext
from app.core.enums import AppSurface, EmailTokenKind, UserRole, UserStatus
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


def _actor(user_id: UUID) -> AuthContext:
    return AuthContext(
        user_id=str(user_id),
        email="demo@koicloud.dev",
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.WEB,
    )


async def test_get_invoice_pdf_renders_iva_pdf() -> None:
    reset_auth_tables()
    billing_commands._FIXTURE_OWNERS.clear()
    async with _make_client() as client:
        user_id, token = await _create_active_user(client, "pdf-wire@koicloud.dev")
        invoice_id = uuid4()
        pdf = await billing_commands.get_invoice_pdf(_actor(user_id), invoice_id)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 1024
        text = pdf.decode("latin-1", errors="ignore")
        assert "IVA" in text
        assert "12" in text
        assert ACADEMIC_FOOTER in text
        assert "KC-" in text

        http = await client.get(
            f"/api/v1/invoices/{invoice_id}/pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert http.status_code == 200
        assert http.headers["content-type"].startswith("application/pdf")


async def test_get_invoice_pdf_not_owner() -> None:
    reset_auth_tables()
    billing_commands._FIXTURE_OWNERS.clear()
    async with _make_client() as client:
        user_a, _ = await _create_active_user(client, "pdf-owner@koicloud.dev")
        user_b, token_b = await _create_active_user(client, "pdf-other@koicloud.dev")
        invoice_id = uuid4()
        await billing_commands.get_invoice_pdf(_actor(user_a), invoice_id)

        http = await client.get(
            f"/api/v1/invoices/{invoice_id}/pdf",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert http.status_code == 403
        assert http.json()["code"] == "not_owner"
        assert user_b != user_a
