from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import PendingConfirmation, User
from app.core.security import generate_confirmation_token, hash_token
from app.core.time import utc_now
from app.schemas import (
    ConfirmationNextStep,
    ConfirmationRequiredResponse,
    CreatePondRequest,
    RestoreBackupRequest,
    RunSQLRequest,
    SubscribeRequest,
    ToggleAgentAccessRequest,
)


async def propose_action(
    *,
    actor: AuthContext,
    action: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> ConfirmationRequiredResponse:
    settings = get_settings()
    token = generate_confirmation_token(action)
    from datetime import timedelta

    expires_at = utc_now().replace(microsecond=0) + timedelta(seconds=settings.confirm_ttl_seconds)
    row = PendingConfirmation(
        user_id=UUID(actor.user_id),
        token_hash=hash_token(token),
        action=action,
        payload=payload or {},
        summary=summary,
        expires_at=expires_at,
    )
    async with SessionLocal() as session:
        session.add(row)
        await session.commit()

    return ConfirmationRequiredResponse(
        status="confirmation_required",
        token=token,
        summary=summary,
        expires_at=expires_at,
        next=ConfirmationNextStep(
            confirm_url=f"/api/v1/confirm/{token}",
            cli_example=f"koicloud confirm {token}",
        ),
    )


async def confirm_action(token: str) -> dict[str, Any]:
    token_hash = hash_token(token)
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(PendingConfirmation).where(PendingConfirmation.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if row is None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.consumed_at is not None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.expires_at <= utc_now():
            raise AppError(ErrorCode.CONFIRMATION_EXPIRED)

        user = await session.get(User, row.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)

        row.consumed_at = utc_now()
        action = row.action
        payload = dict(row.payload)
        await session.commit()

    actor = AuthContext(
        user_id=str(user.id),
        email=user.email,
        role=user.role if isinstance(user.role, UserRole) else UserRole(str(user.role)),
        status=UserStatus.ACTIVE,
        surface=AppSurface.MCP,
    )
    return await _dispatch(action, payload, actor=actor, confirm_token=token)


async def discard_pending_confirmation(token: str) -> None:
    token_hash = hash_token(token)
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(PendingConfirmation).where(PendingConfirmation.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if row is None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.consumed_at is not None:
            return
        row.consumed_at = utc_now()
        await session.commit()


async def _dispatch(
    action: str,
    payload: dict[str, Any],
    *,
    actor: AuthContext,
    confirm_token: str,
) -> dict[str, Any]:
    from app.commands import agent_access as agent_access_commands
    from app.commands import backups as backup_commands
    from app.commands import billing as billing_commands
    from app.commands import ponds as pond_commands
    from app.commands import sql as sql_commands

    if action == "create_pond":
        result = await pond_commands.create_pond(
            CreatePondRequest.model_validate(payload),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "delete_pond":
        result = await pond_commands.delete_pond(
            actor,
            UUID(str(payload["pond_id"])),
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "retry_failed_job":
        result = await pond_commands.retry_failed_job(
            UUID(str(payload["pond_id"])),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "subscribe":
        result = await billing_commands.subscribe(
            SubscribeRequest.model_validate(payload),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "cancel_subscription":
        result = await billing_commands.cancel_subscription(
            UUID(str(payload["subscription_id"])),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "trigger_backup":
        result = await backup_commands.trigger_backup(
            UUID(str(payload["pond_id"])),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "restore_backup":
        result = await backup_commands.restore_backup(
            UUID(str(payload["pond_id"])),
            RestoreBackupRequest.model_validate({"backup_id": payload["backup_id"]}),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action in {"run_sql_write", "run_sql"}:
        result = await sql_commands.run_sql(
            UUID(str(payload["pond_id"])),
            RunSQLRequest.model_validate(payload["request"]),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "rotate_agent_password":
        result = await agent_access_commands.rotate_agent_password(
            actor=actor,
            surface=AppSurface.CLI,
            confirm_token=confirm_token,
        )
    elif action == "toggle_agent_access":
        result = await agent_access_commands.toggle_agent_access(
            ToggleAgentAccessRequest.model_validate(payload),
            actor=actor,
            surface=AppSurface.CLI,
            confirm_token=confirm_token,
        )
    else:
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)

    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return dict(result)
