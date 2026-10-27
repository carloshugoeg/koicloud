"""Preview-only helpers: keep the control-plane node fresh and drain jobs inline.

Enabled when Settings.koi_preview_mock is true (Vercel preview / KOI_PREVIEW_MOCK=1).
Never used against production data.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.enums import JobStatus, JobType, NodeStatus
from app.core.models import Job, Node
from app.core.time import utc_now
from app.modules.jobs.service import JobService
from app.schemas import CompleteJobRequest


async def refresh_preview_node(session: AsyncSession, settings: Settings) -> Node | None:
    if not settings.koi_preview_mock:
        return None
    node = await session.get(Node, settings.node_id)
    if node is None:
        return None
    node.status = NodeStatus.ALIVE
    node.last_seen_at = utc_now()
    node.public_host = settings.node_public_host
    await session.flush()
    return node


async def drain_preview_jobs(
    session: AsyncSession,
    settings: Settings,
    *,
    pond_id: UUID | None = None,
    limit: int = 16,
) -> int:
    """Synchronously complete queued jobs so ponds reach running/deleted without a node-agent."""
    if not settings.koi_preview_mock:
        return 0
    jobs = JobService(session, settings)
    completed = 0
    for _ in range(limit):
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.QUEUED)
            .order_by(Job.created_at.asc())
            .limit(1)
        )
        if pond_id is not None:
            stmt = stmt.where(Job.pond_id == pond_id)
        job = (await session.execute(stmt)).scalar_one_or_none()
        if job is None:
            break
        result: dict[str, object] = {}
        if job.type == JobType.BACKUP_POND:
            backup_id = (job.payload or {}).get("backup_id")
            result = {
                "backup": {
                    "path": f"/tmp/koi-preview/{job.pond_id}/{backup_id or job.id}.dump",
                    "size_bytes": 128,
                    "sha256": "0" * 64,
                }
            }
        await jobs.complete(
            str(job.id),
            CompleteJobRequest(status="succeeded", result=result or None, error=None),
        )
        completed += 1
        await session.flush()
    return completed
