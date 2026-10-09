from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, InvoiceStatus, SubscriptionStatus
from app.core.models import Invoice, Subscription
from app.core.time import utc_now
from app.main import app
from app.modules.auth import AuthService
from app.workers.daily_renewal import tick
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(client: AsyncClient, email: str) -> tuple[UUID, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Renewal User"},
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


async def _expire(subscription_id: str, *, cancel_at_period_end: bool = False) -> None:
    async with SessionLocal() as session:
        sub = await session.get(Subscription, UUID(subscription_id))
        assert sub is not None
        sub.current_period_end = utc_now() - timedelta(minutes=1)
        sub.cancel_at_period_end = cancel_at_period_end
        await session.commit()


async def _tick() -> object:
    async with SessionLocal() as session:
        return await tick(session)


def test_daily_renewal_renews_via_billing_service() -> None:
    reset_auth_tables()

    async def scenario():
        async with _make_client() as client:
            _, token = await _create_active_user(client, "renew-ok@koicloud.dev")
            body = await _subscribe(client, token)
            sub_id = body["subscription"]["id"]
            first_invoice = body["invoice"]["id"]
            await _expire(sub_id)
            stats = await _tick()
            assert stats.skipped_lock is False
            assert stats.renewed == 1
            assert stats.closed == 0

            async with SessionLocal() as session:
                sub = await session.get(Subscription, UUID(sub_id))
                assert sub is not None
                assert sub.status == SubscriptionStatus.ACTIVE
                assert sub.current_period_end > utc_now()
                invoices = (
                    await session.scalars(
                        select(Invoice)
                        .where(Invoice.subscription_id == UUID(sub_id))
                        .order_by(Invoice.issued_at.asc())
                    )
                ).all()
                assert len(invoices) == 2
                assert str(invoices[0].id) == first_invoice
                assert invoices[1].status == InvoiceStatus.PAID
                assert invoices[1].number != invoices[0].number

            again = await _tick()
            assert again.renewed == 0
            assert again.closed == 0

    asyncio.run(scenario())


def test_daily_renewal_closes_cancel_at_period_end() -> None:
    reset_auth_tables()

    async def scenario():
        async with _make_client() as client:
            _, token = await _create_active_user(client, "renew-cancel@koicloud.dev")
            body = await _subscribe(client, token)
            sub_id = body["subscription"]["id"]
            await _expire(sub_id, cancel_at_period_end=True)
            stats = await _tick()
            assert stats.closed == 1
            assert stats.renewed == 0

            async with SessionLocal() as session:
                sub = await session.get(Subscription, UUID(sub_id))
                assert sub is not None
                assert sub.status == SubscriptionStatus.CANCELED
                invoices = (
                    await session.scalars(
                        select(Invoice).where(Invoice.subscription_id == UUID(sub_id))
                    )
                ).all()
                assert len(invoices) == 1

    asyncio.run(scenario())


def test_daily_renewal_skips_active_in_period() -> None:
    reset_auth_tables()

    async def scenario():
        async with _make_client() as client:
            _, token = await _create_active_user(client, "renew-skip@koicloud.dev")
            await _subscribe(client, token)
            stats = await _tick()
            assert stats.renewed == 0
            assert stats.closed == 0

    asyncio.run(scenario())
