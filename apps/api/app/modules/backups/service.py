from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.config import Settings
from app.core.enums import (
    BackupKind,
    BackupStatus,
    JobStatus,
    JobType,
    PondDesiredState,
    PondObservedState,
)
from app.core.errors import AppError, ErrorCode
from app.core.models import Backup, Job, Pond, PondStatus
from app.core.time import utc_now
from app.modules.ponds.service import PondService, job_to_out
from app.schemas import BackupOut, JobOut


def backup_to_out(backup: Backup) -> BackupOut:
    return BackupOut(
        id=backup.id,
        pond_id=backup.pond_id,
        kind=backup.kind,
        status=backup.status,
        storage_path=backup.storage_path,
        size_bytes=int(backup.size_bytes or 0),
        sha256=backup.sha256 or "",
        created_at=backup.created_at,
        completed_at=backup.completed_at,
    )


class BackupService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.ponds = PondService(session, settings)

    async def list_for_owned(self, actor: AuthContext, pond_id: UUID) -> list[BackupOut]:
        await self.ponds.get_owned(actor, pond_id)
        rows = (
            await self.session.execute(
                select(Backup)
                .where(Backup.pond_id == pond_id)
                .order_by(Backup.created_at.desc())
            )
        ).scalars()
        return [backup_to_out(row) for row in rows]

    async def trigger_on_demand(
        self, actor: AuthContext, pond_id: UUID
    ) -> tuple[BackupOut, JobOut]:
        pond, _status = await self.ponds.get_owned(actor, pond_id)
        await self.ponds._assert_no_active_job(pond.id)
        backup, job = await self.enqueue_backup(pond=pond, kind=BackupKind.ON_DEMAND)
        return backup_to_out(backup), job_to_out(job)

    async def restore(self, actor: AuthContext, pond_id: UUID, backup_id: UUID) -> JobOut:
        pond, status = await self.ponds.get_owned(actor, pond_id)
        backup = await self.session.get(Backup, backup_id)
        if backup is None or backup.pond_id != pond.id or backup.status != BackupStatus.SUCCEEDED:
            raise AppError(ErrorCode.POND_NOT_FOUND)
        await self.ponds._assert_no_active_job(pond.id)

        status.observed_state = PondObservedState.RESTORING
        status.healthy = False
        status.updated_at = utc_now()

        job = Job(
            type=JobType.RESTORE_POND,
            pond_id=pond.id,
            node_id=pond.node_id,
            status=JobStatus.QUEUED,
            payload={
                **self.ponds._agent_payload(pond),
                "backup_id": str(backup.id),
            },
        )
        self.session.add(job)
        await self.session.flush()
        return job_to_out(job)

    async def enqueue_daily_for_running(self) -> list[JobOut]:
        rows = (
            await self.session.execute(
                select(Pond, PondStatus)
                .join(PondStatus, PondStatus.pond_id == Pond.id)
                .where(
                    Pond.desired_state == PondDesiredState.RUNNING,
                    PondStatus.observed_state == PondObservedState.RUNNING,
                )
                .order_by(Pond.created_at.asc())
            )
        ).all()
        jobs: list[JobOut] = []
        for pond, _status in rows:
            active = (
                await self.session.execute(
                    select(Job.id).where(
                        Job.pond_id == pond.id,
                        Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
                    )
                )
            ).scalar_one_or_none()
            if active is not None:
                continue
            _backup, job = await self.enqueue_backup(pond=pond, kind=BackupKind.DAILY)
            jobs.append(job_to_out(job))
        return jobs

    async def enqueue_backup(self, *, pond: Pond, kind: BackupKind) -> tuple[Backup, Job]:
        backup = Backup(
            pond_id=pond.id,
            kind=kind,
            status=BackupStatus.QUEUED,
            storage_path=str(Path(self.settings.backup_dir) / pond.name / "pending.dump"),
            size_bytes=0,
            sha256="",
        )
        self.session.add(backup)
        await self.session.flush()
        backup.storage_path = str(
            Path(self.settings.backup_dir) / pond.name / f"{backup.id}.dump"
        )
        job = Job(
            type=JobType.BACKUP_POND,
            pond_id=pond.id,
            node_id=pond.node_id,
            status=JobStatus.QUEUED,
            payload={
                **self.ponds._agent_payload(pond),
                "backup_id": str(backup.id),
            },
        )
        self.session.add(job)
        await self.session.flush()
        return backup, job
