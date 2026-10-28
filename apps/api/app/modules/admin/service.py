from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.commands import admin as admin_commands
from app.core.auth import AuthContext
from app.core.db import SessionLocal
from app.core.enums import ActorKind, PondDesiredState, PondObservedState
from app.core.models import AuditEvent, Pond, PondStatus, User
from app.modules.metering.samples import latest_sample_size_by_pond
from app.schemas import (
    AdminPondListResponse,
    AdminPondOut,
    AdminTotalsOut,
    AdminTotalsResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AuditEventListResponse,
    AuditEventOut,
    SuspendUserRequest,
)

SENSITIVE_AUDIT_ACTIONS = (
    "suspend_user",
    "reveal_agent_access",
    "delete_pond",
    "restore_backup",
    "user.delete",
)


class AdminService:
    @staticmethod
    async def list_users() -> AdminUserListResponse:
        return await admin_commands.admin_list_users()

    @staticmethod
    async def suspend_user(
        user_id: UUID,
        payload: SuspendUserRequest,
        *,
        actor: AuthContext | None = None,
    ) -> AdminUserResponse:
        return await admin_commands.suspend_user(user_id, payload, actor=actor)

    @staticmethod
    async def reactivate_user(user_id: UUID) -> AdminUserResponse:
        return await admin_commands.reactivate_user(user_id)

    @staticmethod
    async def list_ponds() -> AdminPondListResponse:
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(Pond, PondStatus, User.email)
                    .join(PondStatus, PondStatus.pond_id == Pond.id)
                    .join(User, User.id == Pond.user_id)
                    .order_by(Pond.created_at.desc())
                )
            ).all()
            sizes = await latest_sample_size_by_pond(session, [pond.id for pond, _, _ in rows])
            ponds = [
                AdminPondOut(
                    id=pond.id,
                    owner_email=owner_email,
                    name=pond.name,
                    plan_id=pond.plan_id,
                    node_id=pond.node_id,
                    desired_state=pond.desired_state,
                    observed_state=status.observed_state,
                    host_port=pond.host_port,
                    created_at=pond.created_at,
                    size_bytes=sizes.get(pond.id),
                    last_error=status.last_error,
                )
                for pond, status, owner_email in rows
            ]
            return AdminPondListResponse(ponds=ponds, next_cursor=None)

    @staticmethod
    async def totals() -> AdminTotalsResponse:
        async with SessionLocal() as session:
            users = int(
                (await session.execute(select(func.count()).select_from(User))).scalar_one()
            )
            ponds = int(
                (
                    await session.execute(
                        select(func.count())
                        .select_from(Pond)
                        .where(Pond.desired_state != PondDesiredState.DELETED)
                    )
                ).scalar_one()
            )
            ponds_running = int(
                (
                    await session.execute(
                        select(func.count())
                        .select_from(PondStatus)
                        .join(Pond, Pond.id == PondStatus.pond_id)
                        .where(
                            PondStatus.observed_state == PondObservedState.RUNNING,
                            Pond.desired_state != PondDesiredState.DELETED,
                        )
                    )
                ).scalar_one()
            )
            return AdminTotalsResponse(
                totals=AdminTotalsOut(
                    users=users, ponds=ponds, ponds_running=ponds_running
                )
            )

    @staticmethod
    async def list_audit() -> AuditEventListResponse:
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(AuditEvent)
                    .where(AuditEvent.action.in_(SENSITIVE_AUDIT_ACTIONS))
                    .order_by(AuditEvent.at.desc())
                )
            ).scalars().all()
            events = [
                AuditEventOut(
                    id=row.id,
                    actor_user_id=row.actor_user_id,
                    actor_kind=ActorKind(row.actor_kind),
                    target_kind=row.target_kind,
                    target_id=str(row.target_id),
                    action=row.action,
                    metadata=dict(row.event_metadata or {}),
                    at=row.at,
                )
                for row in rows
            ]
            return AuditEventListResponse(events=events, next_cursor=None)
