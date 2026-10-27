"""CCR #126 / E1-05 — change-password, delete_me, resend-verification, password min 10."""

from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, SubscriptionStatus
from app.core.models import AuditEvent, EmailToken, RefreshToken, Subscription, User
from app.core.rate_limit import reset_rate_limits
from app.core.security import hash_token
from app.main import app
from app.modules.auth import AuthService
from tests.db_reset import reset_auth_tables, reset_pond_tables

PASSWORD = "Sup3rSegura!2026"
NEW_PASSWORD = "NuevaClave!2026"
WEAK_9 = "123456789"  # 9 chars → password_too_weak


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_verify_login(
    client: AsyncClient,
    email: str,
    *,
    password: str = PASSWORD,
    full_name: str = "Account User",
) -> tuple[UUID, str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg.status_code == 201, reg.text
    user_id = UUID(reg.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    verify = await client.post("/api/v1/auth/verify", json={"token": token})
    assert verify.status_code == 200
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    return user_id, body["access_token"], body["refresh_token"]


async def test_password_min_10_register_reset_change() -> None:
    reset_auth_tables()
    reset_rate_limits()

    async with _make_client() as client:
        weak_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak9@koicloud.dev",
                "password": WEAK_9,
                "full_name": "Weak Nine",
            },
        )
        assert weak_reg.status_code == 422
        assert weak_reg.json()["code"] == "password_too_weak"

        user_id, access, _refresh = await _register_verify_login(
            client, "pwdfloor@koicloud.dev"
        )

        reset_token = await AuthService.issue_email_token(
            user_id, EmailTokenKind.RESET_PASSWORD
        )
        weak_reset = await client.post(
            "/api/v1/auth/reset",
            json={"token": reset_token, "new_password": WEAK_9},
        )
        assert weak_reset.status_code == 422
        assert weak_reset.json()["code"] == "password_too_weak"

        weak_change = await client.post(
            "/api/v1/me/change-password",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": PASSWORD, "new_password": WEAK_9},
        )
        assert weak_change.status_code == 422
        assert weak_change.json()["code"] == "password_too_weak"


async def test_change_password_revokes_other_refresh() -> None:
    reset_auth_tables()
    reset_rate_limits()

    async with _make_client() as client:
        _user_id, access, refresh_a = await _register_verify_login(
            client, "changepw@koicloud.dev"
        )
        # Second session
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": "changepw@koicloud.dev", "password": PASSWORD},
        )
        assert login_b.status_code == 200
        refresh_b = login_b.json()["refresh_token"]

        change = await client.post(
            "/api/v1/me/change-password",
            headers={"Authorization": f"Bearer {access}"},
            cookies={"koi_refresh": refresh_a},
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert change.status_code == 204, change.text

        # Current refresh kept; other revoked
        keep = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_a},
        )
        assert keep.status_code == 200, keep.text

        gone = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_b},
        )
        assert gone.status_code == 401
        assert gone.json()["code"] == "token_invalid"

        # New password works; old does not
        bad = await client.post(
            "/api/v1/auth/login",
            json={"email": "changepw@koicloud.dev", "password": PASSWORD},
        )
        assert bad.status_code == 401
        good = await client.post(
            "/api/v1/auth/login",
            json={"email": "changepw@koicloud.dev", "password": NEW_PASSWORD},
        )
        assert good.status_code == 200


async def test_change_password_wrong_current() -> None:
    reset_auth_tables()
    reset_rate_limits()

    async with _make_client() as client:
        _user_id, access, _refresh = await _register_verify_login(
            client, "wrongcur@koicloud.dev"
        )
        res = await client.post(
            "/api/v1/me/change-password",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "NotThePassword!", "new_password": NEW_PASSWORD},
        )
        assert res.status_code == 401
        assert res.json()["code"] == "invalid_credentials"


async def test_delete_me_email_mismatch_and_soft_delete() -> None:
    reset_pond_tables()
    reset_rate_limits()

    async with _make_client() as client:
        user_id, access, _refresh = await _register_verify_login(
            client, "deleteme@koicloud.dev"
        )

        # Ensure a live subscription via pond create
        create = await client.post(
            "/api/v1/ponds",
            headers={"Authorization": f"Bearer {access}"},
            json={"name": "pond-delete-me", "engine_version": "16"},
        )
        assert create.status_code in (200, 201, 202), create.text

        mismatch = await client.request(
            "DELETE",
            "/api/v1/me",
            headers={"Authorization": f"Bearer {access}"},
            json={"confirm_email": "otro@koicloud.dev"},
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["code"] == "email_mismatch"

        deleted = await client.request(
            "DELETE",
            "/api/v1/me",
            headers={"Authorization": f"Bearer {access}"},
            json={"confirm_email": "deleteme@koicloud.dev"},
        )
        assert deleted.status_code == 202, deleted.text
        assert deleted.json() == {"ok": True}

        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            assert user.deleted_at is not None
            assert str(user.email).endswith(f".deleted.{user_id}")
            subs = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == user_id)
                )
            ).scalars().all()
            assert subs
            assert all(s.status == SubscriptionStatus.CANCELED for s in subs)
            audits = (
                await session.execute(
                    select(AuditEvent).where(
                        AuditEvent.action == "user.delete",
                        AuditEvent.target_id == user_id,
                    )
                )
            ).scalars().all()
            assert len(audits) == 1
            tokens = (
                await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.user_id == user_id,
                        RefreshToken.revoked_at.is_(None),
                    )
                )
            ).scalars().all()
            assert tokens == []

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "deleteme@koicloud.dev", "password": PASSWORD},
        )
        assert login.status_code == 401
        assert login.json()["code"] == "invalid_credentials"


async def test_resend_verification_always_202_and_rate_limit() -> None:
    reset_auth_tables()
    reset_rate_limits()

    async with _make_client() as client:
        unknown = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nobody@koicloud.dev"},
        )
        assert unknown.status_code == 202
        assert unknown.json() == {"ok": True}

        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "resend@koicloud.dev",
                "password": PASSWORD,
                "full_name": "Resend User",
            },
        )
        assert reg.status_code == 201
        user_id = UUID(reg.json()["user_id"])

        ok = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "resend@koicloud.dev"},
        )
        assert ok.status_code == 202
        assert ok.json() == {"ok": True}

        async with SessionLocal() as session:
            tokens = (
                await session.execute(
                    select(EmailToken).where(
                        EmailToken.user_id == user_id,
                        EmailToken.kind == EmailTokenKind.VERIFY_EMAIL,
                        EmailToken.consumed_at.is_(None),
                    )
                )
            ).scalars().all()
            assert len(tokens) >= 2

        # 3/min/IP: two already used above + one more ok, then limited
        third = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nobody@koicloud.dev"},
        )
        assert third.status_code == 202
        limited = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nobody@koicloud.dev"},
        )
        assert limited.status_code == 429
        assert limited.json()["code"] == "rate_limited"


async def test_migration_users_deleted_at_up_down() -> None:
    """Smoke: column exists after upgrade; downgrade removes it; re-upgrade restores."""
    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    command.downgrade(cfg, "0004_billing_payment_port")
    async with SessionLocal() as session:
        cols = (
            await session.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'deleted_at'
                    """
                )
            )
        ).scalars().all()
        assert cols == []

    command.upgrade(cfg, "head")
    async with SessionLocal() as session:
        cols = (
            await session.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'deleted_at'
                    """
                )
            )
        ).scalars().all()
        assert cols == ["deleted_at"]


async def test_change_password_keeps_hashed_current_refresh_row() -> None:
    reset_auth_tables()
    reset_rate_limits()

    async with _make_client() as client:
        user_id, access, refresh = await _register_verify_login(
            client, "keeprefresh@koicloud.dev"
        )
        await client.post(
            "/api/v1/me/change-password",
            headers={"Authorization": f"Bearer {access}"},
            cookies={"koi_refresh": refresh},
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        async with SessionLocal() as session:
            row = (
                await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.user_id == user_id,
                        RefreshToken.token_hash == hash_token(refresh),
                    )
                )
            ).scalar_one()
            assert row.revoked_at is None
