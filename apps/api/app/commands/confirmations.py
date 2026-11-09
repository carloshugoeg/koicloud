from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from app.commands.temp_sql_confirmation import (
    assert_grant_matches_request,
    canonical_temp_sql_digest,
    confirmation_expiry,
    digests_equal,
    grant_from_claim,
    is_temp_actor,
    lock_live_pond_token,
    require_temp_write_request,
)
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface, SQLMode, UserRole, UserStatus
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
    now = utc_now().replace(microsecond=0)
    body = payload or {}

    if is_temp_actor(actor):
        return await _propose_temp(
            actor=actor,
            action=action,
            payload=body,
            token=token,
            now=now,
        )

    expires_at = now + timedelta(seconds=settings.confirm_ttl_seconds)
    row = PendingConfirmation(
        user_id=UUID(actor.user_id),
        token_hash=hash_token(token),
        action=action,
        payload=body,
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


async def _propose_temp(
    *,
    actor: AuthContext,
    action: str,
    payload: dict[str, Any],
    token: str,
    now,
) -> ConfirmationRequiredResponse:
    if action != "run_sql_write":
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
    if actor.pond_token_id is None or actor.pond_id is None:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

    request = RunSQLRequest.model_validate(payload.get("request") or {})
    require_temp_write_request(request)
    pond_id = UUID(str(payload["pond_id"]))
    if str(pond_id) != actor.pond_id:
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)

    async with SessionLocal() as session:
        token_row = await lock_live_pond_token(
            session,
            pond_token_id=UUID(actor.pond_token_id),
            actor=actor,
            now=now,
        )
        if token_row.pond_id != pond_id:
            raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)

        digest = canonical_temp_sql_digest(
            pond_token_id=token_row.id,
            pond_id=pond_id,
            query=request.query,
        )
        expires_at = confirmation_expiry(
            now=now,
            pond_token_expires_at=token_row.expires_at,
        )
        ttl_seconds = max(0, int((expires_at - now).total_seconds()))
        ttl_minutes = max(1, ttl_seconds // 60) if ttl_seconds else 1
        bound_summary = (
            f"Se ejecutará SQL en modo write sobre el pond '{pond_id}' para {actor.email}. "
            f"Confirmá con confirm_action(token) en MCP (/mcp). "
            f"Expira en {ttl_minutes} min."
        )
        row = PendingConfirmation(
            user_id=UUID(actor.user_id),
            token_hash=hash_token(token),
            action=action,
            payload={
                "pond_id": str(pond_id),
                "request": {"query": request.query, "mode": "write"},
            },
            summary=bound_summary,
            expires_at=expires_at,
            pond_token_id=token_row.id,
            pond_id=pond_id,
            request_digest=digest,
        )
        session.add(row)
        await session.commit()

    return ConfirmationRequiredResponse(
        status="confirmation_required",
        token=token,
        summary=bound_summary,
        expires_at=expires_at,
        next=ConfirmationNextStep(
            confirm_url="/mcp",
            cli_example="",
        ),
    )


async def confirm_action(token: str, *, actor: AuthContext | None = None) -> dict[str, Any]:
    if actor is not None and is_temp_actor(actor):
        return await _confirm_temp(token, actor=actor)
    return await _confirm_owner(token, actor=actor)


async def _confirm_temp(token: str, *, actor: AuthContext) -> dict[str, Any]:
    token_hash = hash_token(token)
    if actor.pond_token_id is None:
        raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)

    async with SessionLocal() as session:
        await lock_live_pond_token(
            session,
            pond_token_id=UUID(actor.pond_token_id),
            actor=actor,
        )
        now = utc_now()
        row = (
            await session.execute(
                select(PendingConfirmation)
                .where(PendingConfirmation.token_hash == token_hash)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None or row.consumed_at is not None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if (
            row.pond_token_id is None
            or row.pond_id is None
            or row.request_digest is None
            or str(row.pond_token_id) != actor.pond_token_id
            or str(row.user_id) != actor.user_id
            or (actor.pond_id is not None and str(row.pond_id) != actor.pond_id)
        ):
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.action != "run_sql_write":
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.expires_at <= now:
            raise AppError(ErrorCode.CONFIRMATION_EXPIRED)

        payload = dict(row.payload)
        try:
            request = RunSQLRequest.model_validate(payload.get("request") or {})
        except Exception as exc:
            raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH) from exc
        if request.mode != SQLMode.WRITE:
            raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
        pond_id = UUID(str(payload.get("pond_id")))
        if pond_id != row.pond_id:
            raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
        expected = canonical_temp_sql_digest(
            pond_token_id=row.pond_token_id,
            pond_id=row.pond_id,
            query=request.query,
        )
        if not digests_equal(row.request_digest, expected):
            raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)

        claimed = (
            await session.execute(
                update(PendingConfirmation)
                .where(
                    PendingConfirmation.id == row.id,
                    PendingConfirmation.consumed_at.is_(None),
                    PendingConfirmation.expires_at > now,
                )
                .values(consumed_at=now)
                .returning(PendingConfirmation.id)
            )
        ).scalar_one_or_none()
        if claimed is None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)

        grant = grant_from_claim(
            confirmation_id=row.id,
            pond_token_id=row.pond_token_id,
            pond_id=row.pond_id,
            request_digest=row.request_digest,
            query=request.query,
        )
        await session.commit()

    return await _dispatch_temp_sql(actor=actor, grant=grant, request=request, pond_id=pond_id)


async def _dispatch_temp_sql(
    *,
    actor: AuthContext,
    grant,
    request: RunSQLRequest,
    pond_id: UUID,
) -> dict[str, Any]:
    from app.commands import sql as sql_commands

    assert_grant_matches_request(
        grant,
        pond_id=pond_id,
        query=request.query,
        mode=request.mode.value if hasattr(request.mode, "value") else str(request.mode),
    )
    result = await sql_commands.run_sql(
        pond_id,
        request,
        actor=actor,
        surface=AppSurface.MCP,
        confirm_token=None,
        temp_grant=grant,
    )
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return dict(result)


async def _confirm_owner(token: str, *, actor: AuthContext | None) -> dict[str, Any]:
    token_hash = hash_token(token)
    async with SessionLocal() as session:
        now = utc_now()
        row = (
            await session.execute(
                select(PendingConfirmation)
                .where(PendingConfirmation.token_hash == token_hash)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.pond_token_id is not None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.consumed_at is not None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.expires_at <= now:
            raise AppError(ErrorCode.CONFIRMATION_EXPIRED)

        user = await session.get(User, row.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if actor is not None and str(user.id) != actor.user_id:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)

        claimed = (
            await session.execute(
                update(PendingConfirmation)
                .where(
                    PendingConfirmation.id == row.id,
                    PendingConfirmation.consumed_at.is_(None),
                    PendingConfirmation.expires_at > now,
                )
                .values(consumed_at=now)
                .returning(PendingConfirmation.id)
            )
        ).scalar_one_or_none()
        if claimed is None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)

        action = row.action
        payload = dict(row.payload)
        await session.commit()

    dispatch_actor = AuthContext(
        user_id=str(user.id),
        email=user.email,
        role=user.role if isinstance(user.role, UserRole) else UserRole(str(user.role)),
        status=UserStatus.ACTIVE,
        surface=AppSurface.MCP,
    )
    return await _dispatch(action, payload, actor=dispatch_actor, confirm_token=token)


async def discard_pending_confirmation(token: str, *, actor: AuthContext | None = None) -> None:
    token_hash = hash_token(token)
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(PendingConfirmation).where(PendingConfirmation.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if row is None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if row.pond_token_id is not None:
            raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)
        if actor is not None and str(row.user_id) != actor.user_id:
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
    elif action == "stop_pond":
        result = await pond_commands.stop_pond(
            actor,
            UUID(str(payload["pond_id"])),
            surface=AppSurface.MCP,
            confirm_token=confirm_token,
        )
    elif action == "start_pond":
        result = await pond_commands.start_pond(
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
