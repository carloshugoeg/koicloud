"""W1-54: sandbox default at register + onboarding-complete flag."""

from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, SubscriptionStatus
from app.core.models import Subscription
from app.core.time import utc_now
from app.main import app
from app.modules.auth import AuthService
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register(client: AsyncClient, email: str) -> UUID:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Onboarding User",
        },
    )
    assert reg.status_code == 201, reg.text
    return UUID(reg.json()["user_id"])


async def _verify_and_login(client: AsyncClient, user_id: UUID, email: str) -> str:
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    verify = await client.post("/api/v1/auth/verify", json={"token": token})
    assert verify.status_code == 200, verify.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


async def test_register_creates_sandbox_subscription_once() -> None:
    reset_auth_tables()
    email = "sandbox-default@koicloud.dev"

    async with _make_client() as client:
        user_id = await _register(client, email)

        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == user_id)
                )
            ).scalars().all()
        assert len(rows) == 1
        assert rows[0].plan_id == "sandbox"
        assert rows[0].status == SubscriptionStatus.ACTIVE

        # Unverified re-register must not insert a second subscription.
        again = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "full_name": "Onboarding User",
            },
        )
        assert again.status_code == 201, again.text
        assert UUID(again.json()["user_id"]) == user_id

        async with SessionLocal() as session:
            count = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == user_id)
                )
            ).scalars().all()
        assert len(count) == 1


async def test_onboarding_flag_defaults_false_and_complete_is_once() -> None:
    reset_auth_tables()
    email = "onboard-flag@koicloud.dev"

    async with _make_client() as client:
        user_id = await _register(client, email)
        access = await _verify_and_login(client, user_id, email)

        me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200, me.text
        user = me.json()["user"]
        assert user["onboarded"] is False
        assert me.json()["subscription"]["plan_id"] == "sandbox"

        first = await client.post(
            "/api/v1/me/onboarding/complete",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert first.status_code == 204, first.text

        me2 = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"})
        assert me2.status_code == 200, me2.text
        assert me2.json()["user"]["onboarded"] is True

        # Idempotent.
        second = await client.post(
            "/api/v1/me/onboarding/complete",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert second.status_code == 204, second.text

        async with SessionLocal() as session:
            row = (
                await session.execute(
                    text("SELECT onboarded_at FROM users WHERE id = :id"),
                    {"id": str(user_id)},
                )
            ).one()
        assert row[0] is not None
        assert row[0] <= utc_now()


async def test_ensure_subscription_does_not_stack_micro_on_sandbox() -> None:
    """Active sandbox (even past period) must not grow a silent Micro row."""
    from app.core.config import get_settings
    from app.core.models import User
    from app.modules.ponds.service import PondService

    reset_auth_tables()
    email = "no-silent-micro@koicloud.dev"

    async with _make_client() as client:
        user_id = await _register(client, email)
        await _verify_and_login(client, user_id, email)

        async with SessionLocal() as session:
            sub = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == user_id)
                )
            ).scalar_one()
            # Force period into the past so the old ensure_subscription path
            # would treat the user as planless and insert Micro.
            sub.current_period_end = utc_now()
            await session.commit()

            user = await session.get(User, user_id)
            assert user is not None
            ensured = await PondService(session, get_settings()).ensure_subscription(user)
            await session.commit()
            assert ensured.plan_id == "sandbox"

            rows = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == user_id)
                )
            ).scalars().all()
        assert len(rows) == 1
        assert rows[0].plan_id == "sandbox"
        assert not any(row.plan_id == "micro" for row in rows)


async def test_create_pond_with_two_active_sandbox_rows() -> None:
    """Duplicate active sandbox rows must not 500 when creating a pond."""
    from datetime import timedelta
    from uuid import uuid4

    from app.core.models import Subscription

    reset_auth_tables()
    email = "two-sandbox@koicloud.dev"

    async with _make_client() as client:
        user_id = await _register(client, email)
        access = await _verify_and_login(client, user_id, email)

        async with SessionLocal() as session:
            first = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == user_id)
                )
            ).scalar_one()
            # Past period so ensure_subscription skips the "current" branch and
            # hits the sandbox lookup that used scalar_one_or_none + order_by.
            first.current_period_end = utc_now() - timedelta(minutes=1)
            session.add(
                Subscription(
                    id=uuid4(),
                    user_id=user_id,
                    plan_id="sandbox",
                    status=SubscriptionStatus.ACTIVE,
                    current_period_start=utc_now() - timedelta(days=2),
                    current_period_end=utc_now() - timedelta(days=1),
                )
            )
            await session.commit()

        created = await client.post(
            "/api/v1/ponds",
            headers={"Authorization": f"Bearer {access}"},
            json={"name": "two-sandbox-pond"},
        )
        assert created.status_code == 202, created.text
        assert created.json()["pond"]["plan_id"] == "sandbox"
        assert created.json()["job"]["type"] == "create_pond"
