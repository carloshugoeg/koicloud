from __future__ import annotations

from app.commands import users as user_commands
from app.core.auth import AuthContext
from app.schemas import MeResponse, UpdateProfileRequest, UserResponse


class UserService:
    """Service encapsulating user profile operations for W3."""

    @staticmethod
    async def get_me(actor: AuthContext) -> MeResponse:
        return await user_commands.get_me(actor)

    @staticmethod
    async def update_profile(
        actor: AuthContext, payload: UpdateProfileRequest
    ) -> UserResponse:
        return await user_commands.update_profile(actor, payload)
