from __future__ import annotations

import jwt

from app.commands import build_user, stable_uuid
from app.core.enums import UserRole
from app.core.errors import AppError, ErrorCode
from app.core.security import decode_token, issue_access_token, issue_refresh_token
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
    VerifyEmailRequest,
)


def _role_for_email(email: str) -> UserRole:
    if email.startswith("admin@"):
        return UserRole.ADMIN
    return UserRole.CLIENT


async def register_user(payload: RegisterUserRequest) -> RegisterUserResponse:
    if payload.email.lower() == "taken@koicloud.dev":
        raise AppError(ErrorCode.EMAIL_TAKEN)
    if len(payload.password) < 8:
        raise AppError(ErrorCode.PASSWORD_TOO_WEAK)
    return RegisterUserResponse(user_id=stable_uuid("user", payload.email), email_verified=False)


async def verify_email(payload: VerifyEmailRequest) -> RegisterUserResponse:
    return RegisterUserResponse(
        user_id=stable_uuid("verified-user", payload.token),
        email_verified=True,
    )


async def issue_tokens(payload: LoginRequest) -> LoginResponse:
    if not payload.email or not payload.password:
        raise AppError(ErrorCode.INVALID_CREDENTIALS)
    if payload.email.startswith("unverified@"):
        raise AppError(ErrorCode.EMAIL_NOT_VERIFIED)
    if payload.email.startswith("suspended@"):
        raise AppError(ErrorCode.ACCOUNT_SUSPENDED)

    role = _role_for_email(payload.email)
    full_name = payload.email.split("@", 1)[0].replace(".", " ").title()
    user = build_user(email=payload.email, full_name=full_name, role=role)

    return LoginResponse(
        access_token=issue_access_token(subject=str(user.id), email=user.email, role=user.role),
        refresh_token=issue_refresh_token(subject=str(user.id), email=user.email),
        user=user,
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

    role = _role_for_email(str(claims.get("email", "user@koicloud.dev")))
    return TokenPairResponse(
        access_token=issue_access_token(
            subject=str(claims["sub"]),
            email=str(claims["email"]),
            role=role,
        ),
        refresh_token=issue_refresh_token(subject=str(claims["sub"]), email=str(claims["email"])),
    )


async def send_reset_token(_: ForgotPasswordRequest) -> OkResponse:
    return OkResponse(ok=True)


async def reset_password(payload: ResetPasswordRequest) -> OkResponse:
    if len(payload.new_password) < 8:
        raise AppError(ErrorCode.PASSWORD_TOO_WEAK)
    return OkResponse(ok=True)


async def revoke_refresh(_: str | None) -> None:
    return None
