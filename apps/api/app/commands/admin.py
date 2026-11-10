from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.core.auth import AuthContext
from app.core.db import SessionLocal
from app.core.deps import ADMIN_USERS_PAGE_LIMIT
from app.core.enums import ActorKind, SubscriptionStatus, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import AuditEvent, Pond, Subscription, User
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


class InvalidUserCursor(Exception):
    pass


@dataclass(frozen=True, slots=True)
class _UserCursor:
    created_at: datetime
    user_id: UUID


def _encode_user_cursor(created_at: datetime, user_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{user_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_user_cursor(token: str) -> _UserCursor:
    padded = token + "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
        stamp, separator, user_id = decoded.partition("|")
        if not separator:
            raise ValueError
        created_at = datetime.fromisoformat(stamp)
        if created_at.tzinfo is None:
            raise ValueError
        return _UserCursor(created_at=created_at, user_id=UUID(user_id))
    except (ValueError, UnicodeError) as exc:
        raise InvalidUserCursor from exc


async def admin_list_users(
    *,
    limit: int = ADMIN_USERS_PAGE_LIMIT,
    cursor: str | None = None,
) -> AdminUserListResponse:
    mark = _decode_user_cursor(cursor) if cursor is not None else None
    async with SessionLocal() as session:
        pond_counts = (
            select(Pond.user_id, func.count().label("ponds_count"))
            .group_by(Pond.user_id)
            .subquery()
        )
        stmt = (
            select(
                User,
                Subscription.plan_id,
                func.coalesce(pond_counts.c.ponds_count, 0),
            )
            .outerjoin(
                Subscription,
                and_(
                    Subscription.user_id == User.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                ),
            )
            .outerjoin(pond_counts, pond_counts.c.user_id == User.id)
            .distinct(User.created_at, User.id)
            .order_by(User.created_at.desc(), User.id.desc(), Subscription.plan_id.asc())
        )
        if mark is not None:
            stmt = stmt.where(
                or_(
                    User.created_at < mark.created_at,
                    and_(User.created_at == mark.created_at, User.id < mark.user_id),
                )
            )
        rows = list((await session.execute(stmt.limit(limit + 1))).all())
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page:
            last_user, _plan_id, _ponds_count = page[-1]
            next_cursor = _encode_user_cursor(last_user.created_at, last_user.id)
        users = [
            _admin_user_out(user, plan_id, int(ponds_count))
            for user, plan_id, ponds_count in page
        ]
        return AdminUserListResponse(users=users, next_cursor=next_cursor)


async def _active_plan_id(session, user_id: UUID) -> str | None:
    return await session.scalar(
        select(Subscription.plan_id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .limit(1)
    )


async def _ponds_count(session, user_id: UUID) -> int:
    return int(
        (
            await session.execute(
                select(func.count()).select_from(Pond).where(Pond.user_id == user_id)
            )
        ).scalar_one()
    )


def _admin_user_out(
    user: User,
    plan_id: str | None,
    ponds_count: int,
) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
        ponds_count=ponds_count,
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
        ponds_count = await _ponds_count(session, user.id)
        return AdminUserResponse(user=_admin_user_out(user, plan_id, ponds_count))


async def reactivate_user(user_id: UUID) -> AdminUserResponse:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(ErrorCode.USER_NOT_FOUND)

        user.status = UserStatus.ACTIVE
        await session.commit()
        await session.refresh(user)
        plan_id = await _active_plan_id(session, user.id)
        ponds_count = await _ponds_count(session, user.id)
        return AdminUserResponse(user=_admin_user_out(user, plan_id, ponds_count))


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
