from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.commands import auth as auth_commands
from app.core.enums import EmailTokenKind
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

REFRESH_COOKIE = "koi_refresh"


class AuthService:
    """Service encapsulating authentication and verification operations for W3."""

    @staticmethod
    async def register_user(payload: RegisterUserRequest) -> RegisterUserResponse:
        # register_user already inserts the verify token and logs plaintext once.
        return await auth_commands.register_user(payload)

    @staticmethod
    async def verify_email(payload: VerifyEmailRequest) -> RegisterUserResponse:
        response = await auth_commands.verify_email(payload)
        return RegisterUserResponse(user_id=response.user_id, email_verified=True)

    @staticmethod
    async def issue_email_token(user_id: UUID, kind: EmailTokenKind) -> str:
        return await auth_commands.issue_email_token(user_id, kind)

    @staticmethod
    async def issue_tokens(payload: LoginRequest) -> LoginResponse:
        return await auth_commands.issue_tokens(payload)

    @staticmethod
    async def rotate_refresh(payload: RefreshTokenRequest) -> TokenPairResponse:
        return await auth_commands.rotate_refresh(payload)

    @staticmethod
    async def logout(
        *,
        refresh_token: str | None,
        user_id: UUID,
        access_jti: str | None = None,
        access_exp: int | None = None,
    ) -> None:
        """Prefer the cookie refresh. Without a cookie, revoke every refresh token for the user."""
        if refresh_token:
            await auth_commands.revoke_refresh(refresh_token)
        else:
            await auth_commands.revoke_all_refresh_tokens(user_id)
        if access_jti is None or access_exp is None:
            return
        await auth_commands.revoke_presented_access(
            user_id=user_id,
            jti=access_jti,
            expires_at=datetime.fromtimestamp(access_exp, tz=UTC),
        )

    @staticmethod
    async def send_reset_token(payload: ForgotPasswordRequest) -> OkResponse:
        return await auth_commands.send_reset_token(payload)

    @staticmethod
    async def reset_password(payload: ResetPasswordRequest) -> OkResponse:
        return await auth_commands.reset_password(payload)
