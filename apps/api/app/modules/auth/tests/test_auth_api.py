from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind
from app.core.errors import AppError, ErrorCode
from app.core.models import EmailToken, User
from app.core.security import hash_token
from app.core.time import utc_now
from app.main import app
from app.modules.auth import AuthService
from app.schemas import RegisterUserRequest, VerifyEmailRequest
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_register_and_verify_api_happy_path() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        # 1. Register user via POST /api/v1/auth/register
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test_api@koicloud.dev",
                "password": PASSWORD,
                "full_name": "API Test User",
                "nit": "0614-100199-102-4",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert set(data.keys()) == {"user_id", "email_verified"}
        assert data["email_verified"] is False
        user_id = UUID(data["user_id"])

        # Verify user exists in DB with email_verified_at as None
        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            assert user.email == "test_api@koicloud.dev"
            assert user.email_verified_at is None

        # 2. Issue email verification token plaintext via AuthService
        token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)

        # 3. Verify email via POST /api/v1/auth/verify with JSON body
        verify_res = await client.post("/api/v1/auth/verify", json={"token": token})
        assert verify_res.status_code == 200
        vdata = verify_res.json()
        assert set(vdata.keys()) == {"user_id", "email_verified"}
        assert vdata["user_id"] == str(user_id)
        assert vdata["email_verified"] is True

        # 4. Check user is now verified in DB
        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            assert user.email_verified_at is not None

        # 5. Token cannot be reused (single-use)
        reused_res = await client.post("/api/v1/auth/verify", json={"token": token})
        assert reused_res.status_code == 401
        assert reused_res.json()["code"] == "token_invalid"


async def test_register_rejects_duplicate_email_and_weak_password_api() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        # Create initial user
        res1 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@koicloud.dev",
                "password": PASSWORD,
                "full_name": "Dup User",
            },
        )
        assert res1.status_code == 201

        # Duplicate email returns 409 email_taken
        res_dup = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@koicloud.dev",
                "password": PASSWORD,
                "full_name": "Dup User Two",
            },
        )
        assert res_dup.status_code == 409
        assert res_dup.json()["code"] == "email_taken"

        # Password shorter than 8 characters returns 422
        res_weak = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@koicloud.dev",
                "password": "short",
                "full_name": "Weak User",
            },
        )
        assert res_weak.status_code == 422

    # Direct AuthService call verifies ErrorCode.PASSWORD_TOO_WEAK
    weak_err = None
    try:
        await AuthService.register_user(
            RegisterUserRequest.model_construct(
                email="weak2@koicloud.dev",
                password="short",
                full_name="Weak Two",
            )
        )
    except AppError as exc:
        weak_err = exc
    assert weak_err is not None
    assert weak_err.code == ErrorCode.PASSWORD_TOO_WEAK
    assert weak_err.http_status == 422


async def test_verify_rejects_expired_and_invalid_tokens_api() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "expire_api@koicloud.dev",
                "password": PASSWORD,
                "full_name": "Expire User",
            },
        )
        assert response.status_code == 201
        user_id = UUID(response.json()["user_id"])

        token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)

        # Manually expire the token in database
        async with SessionLocal() as session:
            row = (
                await session.execute(
                    select(EmailToken).where(EmailToken.token_hash == hash_token(token))
                )
            ).scalar_one()
            row.expires_at = utc_now() - timedelta(minutes=5)
            await session.commit()

        # Expired token returns 401 token_expired
        exp_res = await client.post("/api/v1/auth/verify", json={"token": token})
        assert exp_res.status_code == 401
        assert exp_res.json()["code"] == "token_expired"

        # Unknown token returns 401 token_invalid
        inv_res = await client.post("/api/v1/auth/verify", json={"token": "verify_nonexistent"})
        assert inv_res.status_code == 401
        assert inv_res.json()["code"] == "token_invalid"


async def test_auth_service_register_user_invokes_both_commands() -> None:
    reset_auth_tables()

    payload = RegisterUserRequest(
        email="service_dual@koicloud.dev",
        password=PASSWORD,
        full_name="Dual Command User",
    )
    result = await AuthService.register_user(payload)
    assert result.email_verified is False

    # Check both user was created and verification token was issued
    async with SessionLocal() as session:
        user = await session.get(User, result.user_id)
        assert user is not None
        assert user.email == "service_dual@koicloud.dev"

        tokens = (
            (await session.execute(select(EmailToken).where(EmailToken.user_id == result.user_id)))
            .scalars()
            .all()
        )
        # Both register_user and issue_email_token added token rows
        assert len(tokens) >= 1
        assert all(t.kind == EmailTokenKind.VERIFY_EMAIL for t in tokens)

    # Verify email via AuthService
    raw_token = await AuthService.issue_email_token(result.user_id, EmailTokenKind.VERIFY_EMAIL)
    verify_res = await AuthService.verify_email(VerifyEmailRequest(token=raw_token))
    assert verify_res.user_id == result.user_id
    assert verify_res.email_verified is True
