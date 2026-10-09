from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, InvoiceStatus, PaymentStatus, SubscriptionStatus
from app.core.models import Invoice, Payment, Subscription
from app.main import app
from app.modules.auth import AuthService
from app.modules.billing.payments.port import PaymentAttempt, PaymentProvider
from app.modules.billing.payments.simulated import SimulatedPaymentProvider
from app.modules.billing.service import BillingService
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(client: AsyncClient, email: str) -> tuple[UUID, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Pay User"},
    )
    assert reg.status_code == 201
    user_id = UUID(reg.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    assert (await client.post("/api/v1/auth/verify", json={"token": token})).status_code == 200
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return user_id, login.json()["access_token"]


class PendingPaymentProvider:
    """Fake adapter that leaves payment pending for confirm_payment tests."""

    def start_payment(self, invoice: Invoice) -> PaymentAttempt:
        return PaymentAttempt(
            status=PaymentStatus.PENDING,
            provider="fake",
            provider_ref=f"pend_{invoice.id}",
            checkout_url="https://example.test/checkout",
        )

    def parse_confirmation(self, raw: object) -> str:
        return str(raw)


async def test_subscribe_simulated_provider_happy_path() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, "pay-sim@koicloud.dev")
        response = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_id": "micro"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["subscription"]["status"] == "active"
        assert data["invoice"]["status"] == "paid"
        assert data["payment"]["status"] == "succeeded"
        assert data["payment"]["method"] == "simulated"


async def test_confirm_payment_from_pending_adapter() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        user_id, _ = await _create_active_user(client, "pay-pend@koicloud.dev")

    from app.core.auth import AuthContext
    from app.core.enums import AppSurface, UserRole, UserStatus

    actor = AuthContext(
        user_id=str(user_id),
        email="pay-pend@koicloud.dev",
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.WEB,
    )
    settings = get_settings()
    async with SessionLocal() as session:
        service = BillingService(session, settings, PendingPaymentProvider())
        result = await service.subscribe(actor, "micro")
        assert result.subscription.status == SubscriptionStatus.PENDING_PAYMENT
        assert result.invoice.status == InvoiceStatus.ISSUED
        assert result.payment.status == PaymentStatus.PENDING
        provider_ref = result.payment.method  # method stores provider name; look up ref
        payment_row = await session.get(Payment, result.payment.id)
        assert payment_row is not None
        confirmed = await service.confirm_payment(payment_row.provider_ref)
        assert confirmed.status == PaymentStatus.SUCCEEDED
        sub = await session.get(Subscription, result.subscription.id)
        inv = await session.get(Invoice, result.invoice.id)
        assert sub is not None and sub.status == SubscriptionStatus.ACTIVE
        assert inv is not None and inv.status == InvoiceStatus.PAID
        await session.commit()
        assert provider_ref == "fake"


async def test_billing_service_has_no_adapter_imports() -> None:
    import ast
    from pathlib import Path

    source = Path("app/modules/billing/service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any("simulated" in name for name in imported)
    assert "app.modules.billing.payments.port" in imported
    assert hasattr(SimulatedPaymentProvider(), "start_payment")
    assert hasattr(SimulatedPaymentProvider(), "parse_confirmation")
    _ = PaymentProvider  # port type stays importable for adapters
