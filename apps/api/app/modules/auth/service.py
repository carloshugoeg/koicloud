from __future__ import annotations

from uuid import UUID

from app.commands import auth as auth_commands
from app.core.enums import EmailTokenKind
from app.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterUserRequest,
    RegisterUserResponse,
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
    async def logout(*, refresh_token: str | None, user_id: UUID) -> None:
        """Prefer revoking the cookie refresh; fall back to revoking the whole family."""
        if refresh_token:
            await auth_commands.revoke_refresh(refresh_token)
            return
        await auth_commands.revoke_all_refresh_tokens(user_id)
