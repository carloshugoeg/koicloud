from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.core.auth import AuthContext
from app.core.db import SessionLocal
from app.core.enums import SubscriptionStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import Pond, Subscription, User
from app.schemas import MeResponse, SubscriptionOut, UpdateProfileRequest, UserOut, UserResponse


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        nit=user.nit,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
    )


def _subscription_out(row: Subscription) -> SubscriptionOut:
    return SubscriptionOut(
        id=row.id,
        user_id=row.user_id,
        plan_id=row.plan_id,
        status=row.status,
        current_period_start=row.current_period_start,
        current_period_end=row.current_period_end,
        cancel_at_period_end=row.cancel_at_period_end,
    )


async def get_me(actor: AuthContext) -> MeResponse:
    user_id = UUID(actor.user_id)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(ErrorCode.TOKEN_INVALID)

        ponds_count = int(
            (
                await session.execute(
                    select(func.count()).select_from(Pond).where(Pond.user_id == user_id)
                )
            ).scalar_one()
        )
        subscription = (
            await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
        ).scalar_one_or_none()

        return MeResponse(
            user=_user_out(user),
            subscription=_subscription_out(subscription) if subscription else None,
            ponds_count=ponds_count,
        )


async def update_profile(actor: AuthContext, payload: UpdateProfileRequest) -> UserResponse:
    user_id = UUID(actor.user_id)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AppError(ErrorCode.TOKEN_INVALID)
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.nit is not None:
            user.nit = payload.nit
        await session.commit()
        await session.refresh(user)
        return UserResponse(user=_user_out(user))
