from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.commands import admin as admin_commands
from app.core.auth import AuthContext
from app.core.db import SessionLocal
from app.core.enums import ActorKind
from app.core.models import AuditEvent, Pond, PondStatus, User
from app.schemas import (
    AdminPondListResponse,
    AdminPondOut,
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
                )
                for pond, status, owner_email in rows
            ]
            return AdminPondListResponse(ponds=ponds, next_cursor=None)

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
