from __future__ import annotations

from uuid import UUID

from app.commands import build_admin_user
from app.core.enums import UserStatus
from app.core.errors import AppError, ErrorCode
from app.schemas import (
    AdminPondListResponse,
    AdminSubscriptionListResponse,
    AdminTotalsResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AuditEventListResponse,
    SuspendUserRequest,
)


async def admin_list_users() -> AdminUserListResponse:
    users = [
        build_admin_user(email="carlos@koicloud.dev", full_name="Carlos Hugo Escobar"),
        build_admin_user(email="suspended@koicloud.dev", full_name="Usuario Suspendido"),
    ]
    users[1].status = UserStatus.SUSPENDED
    return AdminUserListResponse(users=users, next_cursor=None)


async def suspend_user(user_id: UUID, payload: SuspendUserRequest) -> AdminUserResponse:
    if payload.confirm_text != "SUSPENDER":
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH, http_status=409)
    user = build_admin_user(email="target@koicloud.dev", full_name="Usuario Objetivo")
    user.id = user_id
    user.status = UserStatus.SUSPENDED
    return AdminUserResponse(user=user)


async def reactivate_user(user_id: UUID) -> AdminUserResponse:
    user = build_admin_user(email="target@koicloud.dev", full_name="Usuario Objetivo")
    user.id = user_id
    return AdminUserResponse(user=user)


async def admin_list_ponds() -> AdminPondListResponse:
    # Late import: AdminService.list_users still imports this module.
    from app.modules.admin.service import AdminService

    return await AdminService.list_ponds()


async def admin_list_subscriptions() -> AdminSubscriptionListResponse:
    from app.modules.admin.service import AdminService

    return await AdminService.list_subscriptions()


async def admin_get_totals() -> AdminTotalsResponse:
    from app.modules.admin.service import AdminService

    return await AdminService.totals()


async def admin_list_audit() -> AuditEventListResponse:
    # Late import: AdminService.list_users still imports this module.
    from app.modules.admin.service import AdminService

    return await AdminService.list_audit()
