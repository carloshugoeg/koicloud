from __future__ import annotations

from uuid import UUID

from sqlalchemy import Column, DateTime, MetaData, Table, Text, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.commands import admin as admin_commands
from app.core.db import SessionLocal
from app.core.enums import ActorKind
from app.core.models import Pond, PondStatus, User
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

_audit_metadata = MetaData()
audit_events = Table(
    "audit_events",
    _audit_metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    Column("actor_user_id", PGUUID(as_uuid=True), nullable=True),
    Column("actor_kind", Text, nullable=False),
    Column("target_kind", Text, nullable=False),
    Column("target_id", PGUUID(as_uuid=True), nullable=False),
    Column("action", Text, nullable=False),
    Column("metadata", JSONB, nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
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
                    select(audit_events)
                    .where(audit_events.c.action.in_(SENSITIVE_AUDIT_ACTIONS))
                    .order_by(audit_events.c.at.desc())
                )
            ).mappings().all()
            events = [
                AuditEventOut(
                    id=row["id"],
                    actor_user_id=row["actor_user_id"],
                    actor_kind=ActorKind(row["actor_kind"]),
                    target_kind=row["target_kind"],
                    target_id=str(row["target_id"]),
                    action=row["action"],
                    metadata=dict(row["metadata"] or {}),
                    at=row["at"],
                )
                for row in rows
            ]
            return AuditEventListResponse(events=events, next_cursor=None)
