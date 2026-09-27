from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.commands.auth import (
    issue_email_token,
    issue_tokens,
    register_user,
    reset_password,
    rotate_refresh,
    send_reset_token,
    verify_email,
)
from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind
from app.core.errors import AppError, ErrorCode
from app.core.models import EmailToken, RefreshToken, User
from app.core.security import hash_token
from app.core.time import utc_now
from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _register_payload(email: str = "jason@koicloud.dev") -> RegisterUserRequest:
    return RegisterUserRequest(
        email=email,
        password=PASSWORD,
        full_name="Jason Gutierrez",
        nit="0614-100199-102-4",
    )


async def test_register_persists_user_and_verify_token() -> None:
    reset_auth_tables()
    created = await register_user(_register_payload())
    assert created.email_verified is False

    async with SessionLocal() as session:
        user = await session.get(User, created.user_id)
        assert user is not None
        assert user.email == "jason@koicloud.dev"
        assert user.email_verified_at is None
        assert user.password_hash != PASSWORD
        tokens = (
            await session.execute(select(EmailToken).where(EmailToken.user_id == user.id))
        ).scalars().all()
        assert len(tokens) == 1
        assert tokens[0].kind == EmailTokenKind.VERIFY_EMAIL
        assert tokens[0].consumed_at is None
        assert tokens[0].expires_at > utc_now()

    taken = None
    try:
        await register_user(_register_payload())
    except AppError as exc:
        taken = exc
    assert taken is not None
    assert taken.code == ErrorCode.EMAIL_TAKEN

    plaintext = await issue_email_token(created.user_id, EmailTokenKind.VERIFY_EMAIL)
    verified = await verify_email(VerifyEmailRequest(token=plaintext))
    assert verified.user_id == created.user_id
    assert verified.email_verified is True

    async with SessionLocal() as session:
        user = await session.get(User, created.user_id)
        assert user is not None
        assert user.email_verified_at is not None
        consumed = (
            await session.execute(
                select(EmailToken).where(EmailToken.token_hash == hash_token(plaintext))
            )
        ).scalar_one()
        assert consumed.consumed_at is not None

    reused = None
    try:
        await verify_email(VerifyEmailRequest(token=plaintext))
    except AppError as exc:
        reused = exc
    assert reused is not None
    assert reused.code == ErrorCode.TOKEN_INVALID


async def test_verify_rejects_expired_and_unknown_tokens() -> None:
    reset_auth_tables()
    created = await register_user(_register_payload("expire@koicloud.dev"))
    plaintext = await issue_email_token(created.user_id, EmailTokenKind.VERIFY_EMAIL)

    async with SessionLocal() as session:
        token = (
            await session.execute(
                select(EmailToken).where(EmailToken.token_hash == hash_token(plaintext))
            )
        ).scalar_one()
        token.expires_at = utc_now() - timedelta(minutes=1)
        await session.commit()

    expired = None
    try:
        await verify_email(VerifyEmailRequest(token=plaintext))
    except AppError as exc:
        expired = exc
    assert expired is not None
    assert expired.code == ErrorCode.TOKEN_EXPIRED

    missing = None
    try:
        await verify_email(VerifyEmailRequest(token="verify_not-a-real-token"))
    except AppError as exc:
        missing = exc
    assert missing is not None
    assert missing.code == ErrorCode.TOKEN_INVALID


async def test_login_persists_refresh_and_reset_revokes_it() -> None:
    reset_auth_tables()
    created = await register_user(_register_payload("login@koicloud.dev"))
    plaintext = await issue_email_token(created.user_id, EmailTokenKind.VERIFY_EMAIL)
    await verify_email(VerifyEmailRequest(token=plaintext))

    unverified = await register_user(_register_payload("pending@koicloud.dev"))
    blocked = None
    try:
        await issue_tokens(LoginRequest(email="pending@koicloud.dev", password=PASSWORD))
    except AppError as exc:
        blocked = exc
    assert blocked is not None
    assert blocked.code == ErrorCode.EMAIL_NOT_VERIFIED
    assert unverified.email_verified is False

    login = await issue_tokens(LoginRequest(email="login@koicloud.dev", password=PASSWORD))
    assert login.user.id == created.user_id
    assert login.user.email_verified is True

    async with SessionLocal() as session:
        stored = (
            await session.execute(
                select(RefreshToken).where(RefreshToken.user_id == created.user_id)
            )
        ).scalars().all()
        assert len(stored) == 1
        assert stored[0].revoked_at is None
        assert stored[0].token_hash == hash_token(login.refresh_token)

    rotated = await rotate_refresh(RefreshTokenRequest(refresh_token=login.refresh_token))
    assert rotated.refresh_token != login.refresh_token

    reused = None
    try:
        await rotate_refresh(RefreshTokenRequest(refresh_token=login.refresh_token))
    except AppError as exc:
        reused = exc
    assert reused is not None
    assert reused.code == ErrorCode.TOKEN_INVALID

    unknown = await send_reset_token(ForgotPasswordRequest(email="ghost@koicloud.dev"))
    assert unknown.ok is True

    known = await send_reset_token(ForgotPasswordRequest(email="login@koicloud.dev"))
    assert known.ok is True
    reset_plain = await issue_email_token(created.user_id, EmailTokenKind.RESET_PASSWORD)
    await reset_password(ResetPasswordRequest(token=reset_plain, new_password="NuevaClave!2026"))

    async with SessionLocal() as session:
        tokens = (
            await session.execute(
                select(RefreshToken).where(RefreshToken.user_id == created.user_id)
            )
        ).scalars().all()
        assert tokens
        assert all(row.revoked_at is not None for row in tokens)

    old_password = None
    try:
        await issue_tokens(LoginRequest(email="login@koicloud.dev", password=PASSWORD))
    except AppError as exc:
        old_password = exc
    assert old_password is not None
    assert old_password.code == ErrorCode.INVALID_CREDENTIALS

    again = await issue_tokens(
        LoginRequest(email="login@koicloud.dev", password="NuevaClave!2026")
    )
    assert again.user.id == created.user_id


async def test_reset_token_is_single_use() -> None:
    reset_auth_tables()
    created = await register_user(_register_payload("reset@koicloud.dev"))
    verify_plain = await issue_email_token(created.user_id, EmailTokenKind.VERIFY_EMAIL)
    await verify_email(VerifyEmailRequest(token=verify_plain))
    reset_plain = await issue_email_token(created.user_id, EmailTokenKind.RESET_PASSWORD)
    await reset_password(ResetPasswordRequest(token=reset_plain, new_password="OtraClave!2026"))

    reused = None
    try:
        await reset_password(ResetPasswordRequest(token=reset_plain, new_password="Tercera!2026"))
    except AppError as exc:
        reused = exc
    assert reused is not None
    assert reused.code == ErrorCode.TOKEN_INVALID


@pytest.mark.parametrize("kind", [EmailTokenKind.VERIFY_EMAIL, EmailTokenKind.RESET_PASSWORD])
async def test_issue_email_token_rejects_unknown_user(kind: EmailTokenKind) -> None:
    from uuid import uuid4

    missing = None
    try:
        await issue_email_token(uuid4(), kind)
    except AppError as exc:
        missing = exc
    assert missing is not None
    assert missing.code == ErrorCode.TOKEN_INVALID
