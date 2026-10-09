from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.enums import (
    BackupKind,
    BackupStatus,
    JobStatus,
    JobType,
    NodeStatus,
    PondDesiredState,
    PondObservedState,
)
from app.core.errors import AppError, ErrorCode
from app.core.models import Backup, Job, Node, Pond, PondStatus
from app.core.security import hash_token
from app.core.time import utc_now
from app.schemas import (
    ClaimedJob,
    ClaimedJobPayload,
    ClaimJobRequest,
    ClaimJobResponse,
    CompleteJobRequest,
)


class JobService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def heartbeat(self) -> None:
        await self._touch_node()

    async def claim(self, payload: ClaimJobRequest) -> ClaimJobResponse | None:
        node = await self._touch_node()
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.QUEUED)
            .order_by(Job.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if payload.max_types:
            stmt = stmt.where(Job.type.in_(payload.max_types))
        job = (await self.session.execute(stmt)).scalar_one_or_none()
        if job is None:
            return None

        job.status = JobStatus.RUNNING
        job.node_id = node.id
        job.claimed_at = utc_now()
        job.attempts += 1

        if job.type == JobType.BACKUP_POND:
            backup_id = (job.payload or {}).get("backup_id")
            if backup_id:
                backup = await self.session.get(Backup, UUID(str(backup_id)))
                if backup is not None and backup.status == BackupStatus.QUEUED:
                    backup.status = BackupStatus.RUNNING

        await self.session.flush()
        return ClaimJobResponse(
            job=ClaimedJob(
                id=job.id,
                type=job.type,
                pond_id=job.pond_id,
                payload=ClaimedJobPayload.model_validate(job.payload),
            )
        )

    async def complete(self, job_id: str, payload: CompleteJobRequest) -> None:
        try:
            parsed_id = UUID(job_id)
        except ValueError as exc:
            raise AppError(ErrorCode.POND_NOT_FOUND) from exc

        job = await self.session.get(Job, parsed_id)
        if job is None:
            raise AppError(ErrorCode.POND_NOT_FOUND)

        now = utc_now()
        job.completed_at = now
        if payload.status == "succeeded":
            job.status = JobStatus.SUCCEEDED
            job.last_error = None
        else:
            job.status = JobStatus.FAILED
            job.last_error = payload.error

        status = await self.session.get(PondStatus, job.pond_id)
        if status is None:
            return
        status.updated_at = now
        status.last_seen_at = now

        if payload.status == "succeeded" and job.type in (
            JobType.CREATE_POND,
            JobType.START_POND,
        ):
            status.observed_state = PondObservedState.RUNNING
            status.healthy = True
            status.last_error = None
        elif payload.status == "succeeded" and job.type == JobType.DELETE_POND:
            status.observed_state = PondObservedState.DELETED
            status.healthy = False
            status.last_error = None
            pond = await self.session.get(Pond, job.pond_id)
            if pond is not None:
                pond.desired_state = PondDesiredState.DELETED
        elif payload.status == "succeeded" and job.type == JobType.BACKUP_POND:
            await self._complete_backup(job, payload, now)
        elif payload.status == "succeeded" and job.type == JobType.RESTORE_POND:
            status.observed_state = PondObservedState.RUNNING
            status.healthy = True
            status.last_error = None
            pond = await self.session.get(Pond, job.pond_id)
            if pond is not None:
                pond.last_restore_at = now
        elif payload.status == "failed" and job.type == JobType.BACKUP_POND:
            await self._fail_backup(job, now)
            if status.observed_state != PondObservedState.DELETING:
                status.observed_state = PondObservedState.FAILED
                status.healthy = False
                status.last_error = payload.error
        elif payload.status == "failed":
            status.observed_state = PondObservedState.FAILED
            status.healthy = False
            status.last_error = payload.error

    async def _complete_backup(
        self, job: Job, payload: CompleteJobRequest, now
    ) -> None:
        backup_id = (job.payload or {}).get("backup_id")
        if not backup_id:
            return
        backup = await self.session.get(Backup, UUID(str(backup_id)))
        if backup is None:
            return

        result = payload.result or {}
        artifact = result.get("backup") if isinstance(result.get("backup"), dict) else result
        if not isinstance(artifact, dict):
            artifact = {}

        backup.status = BackupStatus.SUCCEEDED
        backup.completed_at = now
        if artifact.get("path"):
            backup.storage_path = str(artifact["path"])
        if artifact.get("size_bytes") is not None:
            backup.size_bytes = int(artifact["size_bytes"])
        if artifact.get("sha256"):
            backup.sha256 = str(artifact["sha256"])
        elif not backup.sha256:
            backup.sha256 = ""

        pond = await self.session.get(Pond, job.pond_id)
        if (
            backup.kind == BackupKind.PRE_DELETE
            and pond is not None
            and pond.desired_state == PondDesiredState.DELETED
        ):
            payload_keys = {
                "name",
                "host_port",
                "memory_mb",
                "cpus",
                "db_password_plain",
                "image",
            }
            delete_payload = {
                key: value
                for key, value in (job.payload or {}).items()
                if key in payload_keys
            }
            self.session.add(
                Job(
                    type=JobType.DELETE_POND,
                    pond_id=pond.id,
                    node_id=pond.node_id,
                    status=JobStatus.QUEUED,
                    payload=delete_payload,
                )
            )

    async def _fail_backup(self, job: Job, now) -> None:
        backup_id = (job.payload or {}).get("backup_id")
        if not backup_id:
            return
        backup = await self.session.get(Backup, UUID(str(backup_id)))
        if backup is None:
            return
        backup.status = BackupStatus.FAILED
        backup.completed_at = now

    async def _touch_node(self) -> Node:
        settings = self.settings
        token_hash = hash_token(settings.node_token)
        node = await self.session.get(Node, settings.node_id)
        if node is None:
            node = Node(
                id=settings.node_id,
                public_host=settings.node_public_host,
                status=NodeStatus.ALIVE,
                capacity_ponds=20,
                last_seen_at=utc_now(),
                token_hash=token_hash,
            )
            self.session.add(node)
            await self.session.flush()
            return node
        node.public_host = settings.node_public_host
        node.status = NodeStatus.ALIVE
        node.last_seen_at = utc_now()
        node.token_hash = token_hash
        return node
