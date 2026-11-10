"""POST /me/change-password — authenticated password change."""

from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind
from app.core.models import RefreshToken
from app.core.security import hash_token
from app.main import app
from app.modules.auth import AuthService
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"
NEW_PASSWORD = "NuevaClave!2026"


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
    assert verify.status_code == 200, verify.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    return user_id, body["access_token"], body["refresh_token"]


async def test_change_password_happy_path_and_wrong_current() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        _user_id, access, refresh = await _register_verify_login(
            client, "changepw@koicloud.dev"
        )

        bad = await client.post(
            "/api/v1/me/change-password",
            headers={"Authorization": f"Bearer {access}"},
            cookies={"koi_refresh": refresh},
            json={"current_password": "WrongPass!2026", "new_password": NEW_PASSWORD},
        )
        assert bad.status_code == 401
        assert bad.json()["code"] == "invalid_credentials"

        ok = await client.post(
            "/api/v1/me/change-password",
            headers={"Authorization": f"Bearer {access}"},
            cookies={"koi_refresh": refresh},
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert ok.status_code == 204, ok.text

        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "changepw@koicloud.dev", "password": PASSWORD},
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "changepw@koicloud.dev", "password": NEW_PASSWORD},
        )
        assert new_login.status_code == 200, new_login.text


async def test_change_password_revokes_other_refresh_tokens() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id, access, refresh_a = await _register_verify_login(
            client, "changepw-sessions@koicloud.dev"
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": "changepw-sessions@koicloud.dev", "password": PASSWORD},
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

        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id)
                )
            ).scalars().all()
            revoked = [row for row in rows if row.revoked_at is not None]
            assert any(row.token_hash == hash_token(refresh_b) for row in revoked)
