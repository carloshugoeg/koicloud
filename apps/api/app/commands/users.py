from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import (
    ActorKind,
    PondDesiredState,
    SubscriptionStatus,
)
from app.core.errors import AppError, ErrorCode
from app.core.models import AuditEvent, Pond, Subscription, User
from app.core.time import utc_now
from app.modules.billing.service import latest_invoice_id_by_subscription, subscription_to_out
from app.modules.ponds.service import PondService
from app.schemas import (
    DeleteMeRequest,
    MeResponse,
    OkResponse,
    UpdateProfileRequest,
    UserOut,
    UserResponse,
)


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


async def _require_active_user(session, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise AppError(ErrorCode.TOKEN_INVALID)
    return user


async def get_me(actor: AuthContext) -> MeResponse:
    user_id = UUID(actor.user_id)
    async with SessionLocal() as session:
        user = await _require_active_user(session, user_id)

        ponds_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(Pond)
                    .where(
                        Pond.user_id == user_id,
                        Pond.desired_state != PondDesiredState.DELETED,
                    )
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
        invoice_id = None
        if subscription is not None:
            invoice_ids = await latest_invoice_id_by_subscription(session, [subscription.id])
            invoice_id = invoice_ids.get(subscription.id)

        return MeResponse(
            user=_user_out(user),
            subscription=(
                subscription_to_out(subscription, invoice_id=invoice_id)
                if subscription
                else None
            ),
            ponds_count=ponds_count,
        )


async def update_profile(actor: AuthContext, payload: UpdateProfileRequest) -> UserResponse:
    user_id = UUID(actor.user_id)
    async with SessionLocal() as session:
        user = await _require_active_user(session, user_id)
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.nit is not None:
            user.nit = payload.nit
        await session.commit()
        await session.refresh(user)
        return UserResponse(user=_user_out(user))


async def delete_me(actor: AuthContext, payload: DeleteMeRequest) -> OkResponse:
    from app.commands import auth as auth_commands

    user_id = UUID(actor.user_id)
    confirm = str(payload.confirm_email).strip().lower()

    async with SessionLocal() as session:
        user = await _require_active_user(session, user_id)
        if user.email.strip().lower() != confirm:
            raise AppError(ErrorCode.EMAIL_MISMATCH)

        # Immediate cancel (CCR #126): status canceled now; not end-of-period.
        live_subs = (
            await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.status.in_(
                        (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE)
                    ),
                )
            )
        ).scalars().all()
        for sub in live_subs:
            sub.status = SubscriptionStatus.CANCELED
            sub.cancel_at_period_end = False

        # Soft-delete + free the email for future registration.
        now = utc_now()
        user.deleted_at = now
        user.email = f"{user.email}.deleted.{user.id}"

        session.add(
            AuditEvent(
                actor_user_id=user_id,
                actor_kind=ActorKind.USER.value,
                target_kind="user",
                target_id=user_id,
                action="user.delete",
                event_metadata={},
                at=now,
            )
        )
        await session.flush()

        # Enqueue pond deletes while the actor still "owns" the rows.
        ponds = (
            await session.execute(
                select(Pond).where(
                    Pond.user_id == user_id,
                    Pond.desired_state != PondDesiredState.DELETED,
                )
            )
        ).scalars().all()
        service = PondService(session, get_settings())
        for pond in ponds:
            try:
                await service.delete(actor, pond.id)
            except AppError as exc:
                if exc.code != ErrorCode.POND_BUSY:
                    raise
                pond.desired_state = PondDesiredState.DELETED

        await session.commit()

    await auth_commands.revoke_all_refresh_tokens(user_id)
    return OkResponse(ok=True)
