from __future__ import annotations

from uuid import UUID

from app.commands import auth as auth_commands
from app.core.enums import EmailTokenKind
from app.schemas import RegisterUserRequest, RegisterUserResponse, VerifyEmailRequest


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
