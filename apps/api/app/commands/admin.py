from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.commands import build_admin_user
from app.core.auth import AuthContext
from app.core.db import SessionLocal
from app.core.enums import ActorKind, SubscriptionStatus, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import AuditEvent, Subscription, User
from app.schemas import (
    AdminPondListResponse,
    AdminSubscriptionListResponse,
    AdminTotalsResponse,
    AdminUserListResponse,
    AdminUserOut,
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


async def _active_plan_id(session, user_id: UUID) -> str | None:
    return await session.scalar(
        select(Subscription.plan_id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .limit(1)
    )


def _admin_user_out(user: User, plan_id: str | None) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
        active_subscription_plan=plan_id,
    )


async def suspend_user(
    user_id: UUID,
    payload: SuspendUserRequest,
    actor: AuthContext | None = None,
) -> AdminUserResponse:
    if payload.confirm_text != "SUSPENDER":
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH, http_status=409)

    metadata: dict[str, str] = {}
    if payload.reason is not None:
        metadata["reason"] = payload.reason

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(ErrorCode.USER_NOT_FOUND)

        user.status = UserStatus.SUSPENDED
        session.add(
            AuditEvent(
                actor_user_id=UUID(actor.user_id) if actor is not None else None,
                actor_kind=ActorKind.ADMIN.value,
                target_kind="user",
                target_id=user_id,
                action="suspend_user",
                event_metadata=metadata,
            )
        )
        await session.commit()
        await session.refresh(user)
        plan_id = await _active_plan_id(session, user.id)
        return AdminUserResponse(user=_admin_user_out(user, plan_id))


async def reactivate_user(user_id: UUID) -> AdminUserResponse:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(ErrorCode.USER_NOT_FOUND)

        user.status = UserStatus.ACTIVE
        await session.commit()
        await session.refresh(user)
        plan_id = await _active_plan_id(session, user.id)
        return AdminUserResponse(user=_admin_user_out(user, plan_id))


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
