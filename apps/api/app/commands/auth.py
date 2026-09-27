from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import EmailToken, RefreshToken, User
from app.core.security import (
    decode_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    issue_access_token,
    issue_refresh_token,
    verify_password,
)
from app.core.time import utc_now
from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    OkResponse,
    RefreshTokenRequest,
    RegisterUserRequest,
    RegisterUserResponse,
    ResetPasswordRequest,
    TokenPairResponse,
    UserOut,
    VerifyEmailRequest,
)

_EMAIL_TOKEN_TTL = {
    EmailTokenKind.VERIFY_EMAIL: timedelta(hours=24),
    EmailTokenKind.RESET_PASSWORD: timedelta(hours=1),
}
_EMAIL_TOKEN_PREFIX = {
    EmailTokenKind.VERIFY_EMAIL: "verify",
    EmailTokenKind.RESET_PASSWORD: "reset",
}


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        nit=user.nit,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
    )


async def _issue_email_token_row(
    session: AsyncSession, user_id: UUID, kind: EmailTokenKind
) -> str:
    plaintext = generate_opaque_token(_EMAIL_TOKEN_PREFIX[kind])
    session.add(
        EmailToken(
            user_id=user_id,
            kind=kind,
            token_hash=hash_token(plaintext),
            expires_at=utc_now() + _EMAIL_TOKEN_TTL[kind],
        )
    )
    await session.flush()
    return plaintext


async def _email_token_for(
    session: AsyncSession, plaintext: str, kind: EmailTokenKind
) -> EmailToken:
    token = (
        await session.execute(
            select(EmailToken).where(EmailToken.token_hash == hash_token(plaintext))
        )
    ).scalar_one_or_none()
    if token is None or token.kind != kind:
        raise AppError(ErrorCode.TOKEN_INVALID)
    if token.consumed_at is not None:
        raise AppError(ErrorCode.TOKEN_INVALID)
    if token.expires_at <= utc_now():
        raise AppError(ErrorCode.TOKEN_EXPIRED)
    return token


async def _refresh_row(session: AsyncSession, plaintext: str) -> RefreshToken | None:
    return (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(plaintext))
        )
    ).scalar_one_or_none()


async def _store_refresh(session: AsyncSession, user_id: UUID, refresh: str) -> None:
    claims = decode_token(refresh)
    session.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(refresh),
            expires_at=datetime.fromtimestamp(int(claims["exp"]), tz=UTC),
        )
    )


async def _revoke_all_refresh(session: AsyncSession, user_id: UUID) -> None:
    rows = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    now = utc_now()
    for row in rows:
        row.revoked_at = now


async def issue_email_token(user_id: UUID, kind: EmailTokenKind) -> str:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(ErrorCode.TOKEN_INVALID)
        plaintext = await _issue_email_token_row(session, user_id, kind)
        await session.commit()
        return plaintext


async def register_user(payload: RegisterUserRequest) -> RegisterUserResponse:
    if len(payload.password) < 8:
        raise AppError(ErrorCode.PASSWORD_TOO_WEAK)

    async with SessionLocal() as session:
        taken = (
            await session.execute(select(User.id).where(User.email == payload.email))
        ).scalar_one_or_none()
        if taken is not None:
            raise AppError(ErrorCode.EMAIL_TAKEN)

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role=UserRole.CLIENT,
            nit=payload.nit,
            status=UserStatus.ACTIVE,
            email_verified_at=None,
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError as exc:
            raise AppError(ErrorCode.EMAIL_TAKEN) from exc

        await _issue_email_token_row(session, user.id, EmailTokenKind.VERIFY_EMAIL)
        await session.commit()
        return RegisterUserResponse(user_id=user.id, email_verified=False)


async def verify_email(payload: VerifyEmailRequest) -> RegisterUserResponse:
    async with SessionLocal() as session:
        token = await _email_token_for(session, payload.token, EmailTokenKind.VERIFY_EMAIL)
        user = await session.get(User, token.user_id)
        if user is None:
            raise AppError(ErrorCode.TOKEN_INVALID)
        token.consumed_at = utc_now()
        user.email_verified_at = utc_now()
        await session.commit()
        return RegisterUserResponse(user_id=user.id, email_verified=True)


async def issue_tokens(payload: LoginRequest) -> LoginResponse:
    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == payload.email))
        ).scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AppError(ErrorCode.INVALID_CREDENTIALS)
        if user.email_verified_at is None:
            raise AppError(ErrorCode.EMAIL_NOT_VERIFIED)
        if user.status == UserStatus.SUSPENDED:
            raise AppError(ErrorCode.ACCOUNT_SUSPENDED)

        access = issue_access_token(subject=str(user.id), email=user.email, role=user.role)
        refresh = issue_refresh_token(subject=str(user.id), email=user.email)
        await _store_refresh(session, user.id, refresh)
        await session.commit()
        return LoginResponse(
            access_token=access,
            refresh_token=refresh,
            user=_user_out(user),
        )


async def rotate_refresh(payload: RefreshTokenRequest) -> TokenPairResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except jwt.ExpiredSignatureError as exc:
        raise AppError(ErrorCode.TOKEN_EXPIRED) from exc
    except jwt.PyJWTError as exc:
        raise AppError(ErrorCode.TOKEN_INVALID) from exc

    if claims.get("token_type") != "refresh":
        raise AppError(ErrorCode.TOKEN_INVALID)

    async with SessionLocal() as session:
        row = await _refresh_row(session, payload.refresh_token)
        if row is None:
            raise AppError(ErrorCode.TOKEN_INVALID)
        if row.revoked_at is not None:
            await _revoke_all_refresh(session, row.user_id)
            await session.commit()
            raise AppError(ErrorCode.TOKEN_INVALID)
        if row.expires_at <= utc_now():
            raise AppError(ErrorCode.TOKEN_EXPIRED)

        user = await session.get(User, row.user_id)
        if user is None:
            raise AppError(ErrorCode.TOKEN_INVALID)
        if user.status == UserStatus.SUSPENDED:
            raise AppError(ErrorCode.ACCOUNT_SUSPENDED)

        row.revoked_at = utc_now()
        access = issue_access_token(subject=str(user.id), email=user.email, role=user.role)
        refresh = issue_refresh_token(subject=str(user.id), email=user.email)
        await _store_refresh(session, user.id, refresh)
        await session.commit()
        return TokenPairResponse(access_token=access, refresh_token=refresh)


async def send_reset_token(payload: ForgotPasswordRequest) -> OkResponse:
    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == payload.email))
        ).scalar_one_or_none()
        if user is not None:
            await _issue_email_token_row(session, user.id, EmailTokenKind.RESET_PASSWORD)
        await session.commit()
    return OkResponse(ok=True)


async def reset_password(payload: ResetPasswordRequest) -> OkResponse:
    if len(payload.new_password) < 8:
        raise AppError(ErrorCode.PASSWORD_TOO_WEAK)

    async with SessionLocal() as session:
        token = await _email_token_for(session, payload.token, EmailTokenKind.RESET_PASSWORD)
        user = await session.get(User, token.user_id)
        if user is None:
            raise AppError(ErrorCode.TOKEN_INVALID)
        token.consumed_at = utc_now()
        user.password_hash = hash_password(payload.new_password)
        await _revoke_all_refresh(session, user.id)
        await session.commit()
    return OkResponse(ok=True)


async def revoke_refresh(token: str | None) -> None:
    if not token:
        return
    async with SessionLocal() as session:
        row = await _refresh_row(session, token)
        if row is None or row.revoked_at is not None:
            return
        row.revoked_at = utc_now()
        await session.commit()
