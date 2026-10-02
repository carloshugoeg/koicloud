from __future__ import annotations

from uuid import UUID

from app.commands import build_confirmation, build_job
from app.core.auth import AuthContext
from app.core.enums import AppSurface, BackupKind, BackupStatus, JobType
from app.schemas import (
    BackupListResponse,
    BackupOut,
    ConfirmationRequiredResponse,
    JobResponse,
    RestoreBackupRequest,
    TriggerBackupResponse,
)


def _requires_confirmation(surface: AppSurface, confirm_token: str | None) -> bool:
    return surface in {AppSurface.CLI, AppSurface.MCP} and not confirm_token


async def list_backups(_: AuthContext, pond_id: UUID) -> BackupListResponse:
    backup = BackupOut.example()
    backup.pond_id = pond_id
    return BackupListResponse(backups=[backup], next_cursor=None)


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
    backup = BackupOut.example()
    backup.pond_id = pond_id
    backup.kind = BackupKind.ON_DEMAND
    backup.status = BackupStatus.QUEUED
    backup.completed_at = None
    job = build_job(job_type=JobType.BACKUP_POND, pond_id=pond_id)
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
    job = build_job(job_type=JobType.RESTORE_POND, pond_id=pond_id)
    return JobResponse(job=job)
