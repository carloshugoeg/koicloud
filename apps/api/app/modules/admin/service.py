from __future__ import annotations

from uuid import UUID

from app.commands import admin as admin_commands
from app.schemas import (
    AdminPondListResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AuditEventListResponse,
    SuspendUserRequest,
)


class AdminService:
    @staticmethod
    async def list_users() -> AdminUserListResponse:
        return await admin_commands.admin_list_users()

    @staticmethod
    async def suspend_user(user_id: UUID, payload: SuspendUserRequest) -> AdminUserResponse:
        return await admin_commands.suspend_user(user_id, payload)

    @staticmethod
    async def reactivate_user(user_id: UUID) -> AdminUserResponse:
        return await admin_commands.reactivate_user(user_id)

    @staticmethod
    async def list_ponds() -> AdminPondListResponse:
        return await admin_commands.admin_list_ponds()

    @staticmethod
    async def list_audit() -> AuditEventListResponse:
        return await admin_commands.admin_list_audit()
