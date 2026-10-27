from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.enums import ActorKind, SubscriptionStatus, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import AuditEvent, Subscription, User
from app.core.time import utc_now
from app.schemas import (
    AdminPondListResponse,
    AdminUserListResponse,
    AdminUserOut,
    AdminUserResponse,
    AuditEventListResponse,
    SuspendUserRequest,
)


def _user_out(user: User, plan_id: str | None) -> AdminUserOut:
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


async def _active_plan_by_user(session, user_ids: list[UUID]) -> dict[UUID, str]:
    if not user_ids:
        return {}
    rows = (
        await session.execute(
            select(Subscription)
            .where(
                Subscription.user_id.in_(user_ids),
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(Subscription.current_period_start.desc())
        )
    ).scalars().all()
    plans: dict[UUID, str] = {}
    for row in rows:
        plans.setdefault(row.user_id, row.plan_id)
    return plans


async def admin_list_users() -> AdminUserListResponse:
    async with SessionLocal() as session:
        users = (
            await session.execute(select(User).order_by(User.created_at.desc()))
        ).scalars().all()
        plans = await _active_plan_by_user(session, [user.id for user in users])
        return AdminUserListResponse(
            users=[_user_out(user, plans.get(user.id)) for user in users],
            next_cursor=None,
        )


async def suspend_user(user_id: UUID, payload: SuspendUserRequest) -> AdminUserResponse:
    if payload.confirm_text != "SUSPENDER":
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH, http_status=409)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No existe el usuario solicitado",
            )
        user.status = UserStatus.SUSPENDED
        session.add(
            AuditEvent(
                actor_user_id=None,
                actor_kind=ActorKind.ADMIN.value,
                target_kind="user",
                target_id=user.id,
                action="suspend_user",
                event_metadata={"confirm_text": payload.confirm_text},
                at=utc_now(),
            )
        )
        await session.commit()
        await session.refresh(user)
        plans = await _active_plan_by_user(session, [user.id])
        return AdminUserResponse(user=_user_out(user, plans.get(user.id)))


async def reactivate_user(user_id: UUID) -> AdminUserResponse:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No existe el usuario solicitado",
            )
        user.status = UserStatus.ACTIVE
        session.add(
            AuditEvent(
                actor_user_id=None,
                actor_kind=ActorKind.ADMIN.value,
                target_kind="user",
                target_id=user.id,
                action="reactivate_user",
                event_metadata={},
                at=utc_now(),
            )
        )
        await session.commit()
        await session.refresh(user)
        plans = await _active_plan_by_user(session, [user.id])
        return AdminUserResponse(user=_user_out(user, plans.get(user.id)))


async def admin_list_ponds() -> AdminPondListResponse:
    # Late import: AdminService.list_users still imports this module.
    from app.modules.admin.service import AdminService

    return await AdminService.list_ponds()


async def admin_list_audit() -> AuditEventListResponse:
    # Late import: AdminService.list_users still imports this module.
    from app.modules.admin.service import AdminService

    return await AdminService.list_audit()
