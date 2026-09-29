from __future__ import annotations

from app.commands import auth as auth_commands
from app.schemas import RegisterUserRequest, RegisterUserResponse, VerifyEmailRequest


class AuthService:
    """Service encapsulating authentication and verification operations for W3."""

    @staticmethod
    async def register_user(payload: RegisterUserRequest) -> RegisterUserResponse:
        return await auth_commands.register_user(payload)

    @staticmethod
    async def verify_email(payload: VerifyEmailRequest) -> RegisterUserResponse:
        return await auth_commands.verify_email(payload)
