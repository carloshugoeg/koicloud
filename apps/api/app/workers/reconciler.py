"""Minimal reconciler (E4-05).

Long-lived process. Every 30 s:

1. Reclaim zombie jobs (running with stale claim).
2. Re-enqueue a correction job when desired ≠ observed and the pond
   has no active job.

Not auto-heal. Follows docs/architecture/diagrams/09-reconciler-heartbeat.mmd.

    cd apps/api && DATABASE_URL=… uv run python -m app.workers.reconciler
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import cast, exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Text

from app.core.config import get_settings
from app.core.crypto import decrypt_secret
from app.core.db import SessionLocal
from app.core.enums import JobStatus, JobType, PondDesiredState, PondObservedState
from app.core.models import Job, Pond, PondStatus
from app.core.time import utc_now

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 30
ZOMBIE_AFTER = timedelta(minutes=2)
MAX_ATTEMPTS = 3
# Fixed session-level advisory lock for the reconciler tick.
ADVISORY_LOCK_KEY = 4_050_930

REMEDIATE: dict[tuple[PondDesiredState, PondObservedState], JobType] = {
    (PondDesiredState.RUNNING, PondObservedState.STOPPED): JobType.START_POND,
    (PondDesiredState.RUNNING, PondObservedState.PENDING): JobType.CREATE_POND,
    (PondDesiredState.RUNNING, PondObservedState.FAILED): JobType.CREATE_POND,
    (PondDesiredState.RUNNING, PondObservedState.DELETED): JobType.CREATE_POND,
    (PondDesiredState.DELETED, PondObservedState.DELETING): JobType.DELETE_POND,
    (PondDesiredState.DELETED, PondObservedState.FAILED): JobType.DELETE_POND,
}


@dataclass(frozen=True)
class ReconcileStats:
    zombies_requeued: int = 0
    zombies_failed: int = 0
    drift_enqueued: int = 0
    skipped_lock: bool = False


def _agent_payload(pond: Pond) -> dict[str, object]:
    password = decrypt_secret(pond.db_password_encrypted)
    return {
        "name": pond.name,
        "host_port": pond.host_port,
        "memory_mb": 512,
        "cpus": 0.5,
        "db_password_plain": password,
        "image": "postgres:16-alpine",
    }


async def _try_lock(session: AsyncSession) -> bool:
    result = await session.execute(
        text("SELECT pg_try_advisory_lock(:key)"),
        {"key": ADVISORY_LOCK_KEY},
    )
    return bool(result.scalar_one())


async def _release_lock(session: AsyncSession) -> None:
    await session.execute(
        text("SELECT pg_advisory_unlock(:key)"),
        {"key": ADVISORY_LOCK_KEY},
    )


async def _reclaim_zombies(session: AsyncSession) -> tuple[int, int]:
    cutoff = utc_now() - ZOMBIE_AFTER
    zombies = (
        await session.scalars(
            select(Job).where(
                Job.status == JobStatus.RUNNING,
                Job.claimed_at.is_not(None),
                Job.claimed_at < cutoff,
            )
        )
    ).all()

    requeued = 0
    failed = 0
    for job in zombies:
        job.status = JobStatus.LOST
        job.attempts += 1
        job.claimed_at = None
        if job.attempts < MAX_ATTEMPTS:
            job.status = JobStatus.QUEUED
            job.node_id = None
            requeued += 1
        else:
            job.status = JobStatus.FAILED
            failed += 1
    return requeued, failed


async def _latest_job(session: AsyncSession, pond_id: UUID, job_type: JobType) -> Job | None:
    return (
        await session.scalars(
            select(Job)
            .where(Job.pond_id == pond_id, Job.type == job_type)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
    ).first()


async def _latest_any_job(session: AsyncSession, pond_id: UUID) -> Job | None:
    return (
        await session.scalars(
            select(Job).where(Job.pond_id == pond_id).order_by(Job.created_at.desc()).limit(1)
        )
    ).first()


async def _resolve_job_type(
    session: AsyncSession,
    pond: Pond,
    observed: PondObservedState,
) -> JobType | None:
    mapped = REMEDIATE.get((pond.desired_state, observed))
    if mapped is None:
        return None
    if pond.desired_state == PondDesiredState.RUNNING and observed == PondObservedState.FAILED:
        last = await _latest_any_job(session, pond.id)
        if last is not None and last.status == JobStatus.FAILED:
            return last.type
    return mapped


async def _exhausted(session: AsyncSession, pond_id: UUID, job_type: JobType) -> bool:
    last = await _latest_job(session, pond_id, job_type)
    return (
        last is not None
        and last.status == JobStatus.FAILED
        and last.attempts >= MAX_ATTEMPTS
    )


async def _enqueue_drift(session: AsyncSession) -> int:
    active = exists(
        select(Job.id).where(
            Job.pond_id == Pond.id,
            Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
        )
    )
    # desired/observed are distinct PG enums; compare as text.
    rows = (
        await session.execute(
            select(Pond, PondStatus)
            .join(PondStatus, PondStatus.pond_id == Pond.id)
            .where(
                cast(Pond.desired_state, Text) != cast(PondStatus.observed_state, Text),
                ~active,
            )
        )
    ).all()

    enqueued = 0
    for pond, status in rows:
        job_type = await _resolve_job_type(session, pond, status.observed_state)
        if job_type is None:
            continue
        if await _exhausted(session, pond.id, job_type):
            continue

        prior = await _latest_job(session, pond.id, job_type)
        payload = dict(prior.payload) if prior and prior.payload else _agent_payload(pond)
        if job_type == JobType.START_POND:
            payload = {"name": pond.name}

        session.add(
            Job(
                type=job_type,
                pond_id=pond.id,
                node_id=pond.node_id,
                status=JobStatus.QUEUED,
                payload=payload,
                attempts=0,
            )
        )
        enqueued += 1
    return enqueued


async def tick(session: AsyncSession) -> ReconcileStats:
    locked = await _try_lock(session)
    if not locked:
        return ReconcileStats(skipped_lock=True)
    try:
        zombies_requeued, zombies_failed = await _reclaim_zombies(session)
        drift_enqueued = await _enqueue_drift(session)
        await session.flush()
        return ReconcileStats(
            zombies_requeued=zombies_requeued,
            zombies_failed=zombies_failed,
            drift_enqueued=drift_enqueued,
        )
    except Exception:
        await session.rollback()
        raise
    finally:
        # Unlock on a clean transaction; rollback above clears a failed one.
        try:
            await _release_lock(session)
        except Exception:
            logger.exception("failed to release reconciler advisory lock")


async def run_once() -> ReconcileStats:
    async with SessionLocal() as session:
        stats = await tick(session)
        await session.commit()
    return stats


async def run_forever() -> None:
    get_settings()
    while True:
        try:
            stats = await run_once()
            logger.info(
                "reconcile tick skipped_lock=%s zombies_requeued=%s zombies_failed=%s drift=%s",
                stats.skipped_lock,
                stats.zombies_requeued,
                stats.zombies_failed,
                stats.drift_enqueued,
            )
        except Exception:
            logger.exception("reconcile tick failed")
        await asyncio.sleep(INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
