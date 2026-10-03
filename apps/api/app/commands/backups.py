from __future__ import annotations

from uuid import UUID

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface
from app.modules.backups.service import BackupService
from app.schemas import (
    BackupListResponse,
    ConfirmationRequiredResponse,
    JobResponse,
    RestoreBackupRequest,
    TriggerBackupResponse,
)


def _requires_confirmation(surface: AppSurface, confirm_token: str | None) -> bool:
    return surface in {AppSurface.CLI, AppSurface.MCP} and not confirm_token


async def list_backups(actor: AuthContext, pond_id: UUID) -> BackupListResponse:
    async with SessionLocal() as session:
        backups = await BackupService(session, get_settings()).list_for_owned(actor, pond_id)
        return BackupListResponse(backups=backups, next_cursor=None)


async def trigger_backup(
    pond_id: UUID,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> TriggerBackupResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return await build_confirmation(
            actor=actor,
            action="trigger_backup",
            summary=f"Se encolará un respaldo manual para el pond '{pond_id}'. Expira en 5 min.",
            payload={"pond_id": str(pond_id)},
        )

    async with SessionLocal() as session:
        backup, job = await BackupService(session, get_settings()).trigger_on_demand(
            actor, pond_id
        )
        await session.commit()
        return TriggerBackupResponse(backup=backup, job=job)


async def restore_backup(
    pond_id: UUID,
    payload: RestoreBackupRequest,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> JobResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return await build_confirmation(
            actor=actor,
            action="restore_backup",
            summary=(
                f"Se restaurará el respaldo '{payload.backup_id}' sobre el pond '{pond_id}'. "
                "Expira en 5 min."
            ),
            payload={"pond_id": str(pond_id), "backup_id": str(payload.backup_id)},
        )

    async with SessionLocal() as session:
        job = await BackupService(session, get_settings()).restore(
            actor, pond_id, payload.backup_id
        )
        await session.commit()
        return JobResponse(job=job)
