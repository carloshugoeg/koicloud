"""Minimal reconciler (E4-05 / W1-17).

Long-lived loop, every 30 seconds. Reclaims stale running jobs and enqueues
one correction when desired and observed differ and the pond has no active job.
Does not change pond desired or observed state. Not auto-heal.

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
from app.core.db import SessionLocal
from app.core.enums import JobStatus, JobType, PondDesiredState, PondObservedState
from app.core.models import Job, Pond, PondStatus
from app.core.time import utc_now
from app.modules.ponds.service import PondService

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 30
ZOMBIE_AFTER = timedelta(minutes=2)
MAX_ATTEMPTS = 3
ADVISORY_LOCK_KEY = 4_050_930

# Skip desired=deleted + observed=running|stopped|deleting: pre_delete must win.
# (deleted, deleting) after a failed backup is a hold, not delete_pond.
REMEDIATE: dict[tuple[PondDesiredState, PondObservedState], JobType] = {
    (PondDesiredState.RUNNING, PondObservedState.STOPPED): JobType.START_POND,
    (PondDesiredState.RUNNING, PondObservedState.PENDING): JobType.CREATE_POND,
    (PondDesiredState.RUNNING, PondObservedState.FAILED): JobType.CREATE_POND,
    (PondDesiredState.RUNNING, PondObservedState.DELETED): JobType.CREATE_POND,
    (PondDesiredState.DELETED, PondObservedState.FAILED): JobType.DELETE_POND,
}

_DRIFT_RETRY_TYPES = frozenset({JobType.CREATE_POND, JobType.START_POND, JobType.DELETE_POND})

_PAYLOAD_KEYS = ("name", "host_port", "memory_mb", "cpus", "db_password_plain", "image")
_ACTIVE = (JobStatus.QUEUED, JobStatus.RUNNING)


@dataclass(frozen=True)
class ReconcileStats:
    zombies_requeued: int = 0
    zombies_failed: int = 0
    drift_enqueued: int = 0
    skipped_lock: bool = False


def _agent_payload(session: AsyncSession, pond: Pond) -> dict[str, object]:
    return PondService(session, get_settings())._agent_payload(pond)


async def _try_lock(session: AsyncSession) -> bool:
    result = await session.execute(
        text("SELECT pg_try_advisory_lock(CAST(:key AS bigint))"),
        {"key": ADVISORY_LOCK_KEY},
    )
    return bool(result.scalar_one())


async def _release_lock(session: AsyncSession) -> None:
    await session.execute(
        text("SELECT pg_advisory_unlock(CAST(:key AS bigint))"),
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
        job.attempts += 1
        job.status = JobStatus.LOST
        if job.attempts < MAX_ATTEMPTS:
            job.status = JobStatus.QUEUED
            job.claimed_at = None
            job.node_id = None
            requeued += 1
        else:
            job.status = JobStatus.FAILED
            failed += 1
    return requeued, failed


async def _latest_job(
    session: AsyncSession, pond_id: UUID, job_type: JobType | None = None
) -> Job | None:
    stmt = select(Job).where(Job.pond_id == pond_id).order_by(Job.created_at.desc()).limit(1)
    if job_type is not None:
        stmt = (
            select(Job)
            .where(Job.pond_id == pond_id, Job.type == job_type)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
    return (await session.scalars(stmt)).first()


def _claimable_payload(
    session: AsyncSession, pond: Pond, prior: Job | None
) -> dict[str, object]:
    if prior is not None and prior.payload and all(key in prior.payload for key in _PAYLOAD_KEYS):
        return dict(prior.payload)
    return _agent_payload(session, pond)


async def _resolve_job_type(
    session: AsyncSession, pond: Pond, observed: PondObservedState
) -> JobType | None:
    # Retry a failed delete_pond while observed is still deleting.
    if (
        pond.desired_state == PondDesiredState.DELETED
        and observed == PondObservedState.DELETING
    ):
        last = await _latest_job(session, pond.id)
        if (
            last is not None
            and last.status == JobStatus.FAILED
            and last.type == JobType.DELETE_POND
        ):
            return JobType.DELETE_POND
        return None

    mapped = REMEDIATE.get((pond.desired_state, observed))
    if mapped is None:
        return None
    if pond.desired_state == PondDesiredState.RUNNING and observed == PondObservedState.FAILED:
        last = await _latest_job(session, pond.id)
        # Never auto-replay backup/restore from drift.
        if (
            last is not None
            and last.status == JobStatus.FAILED
            and last.type in _DRIFT_RETRY_TYPES
        ):
            return last.type
    return mapped


async def _enqueue_drift(session: AsyncSession) -> int:
    active = exists(
        select(Job.id).where(
            Job.pond_id == Pond.id,
            Job.status.in_(_ACTIVE),
        )
    )
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
        prior = await _latest_job(session, pond.id, job_type)
        # Carry claim count across requeues so the cap is real (claim increments).
        chain_attempts = (
            prior.attempts
            if prior is not None and prior.status == JobStatus.FAILED
            else 0
        )
        if chain_attempts >= MAX_ATTEMPTS:
            continue
        session.add(
            Job(
                type=job_type,
                pond_id=pond.id,
                node_id=pond.node_id,
                status=JobStatus.QUEUED,
                payload=_claimable_payload(session, pond, prior),
                attempts=chain_attempts,
            )
        )
        enqueued += 1
    return enqueued


async def tick(session: AsyncSession) -> ReconcileStats:
    if not await _try_lock(session):
        return ReconcileStats(skipped_lock=True)
    try:
        zombies_requeued, zombies_failed = await _reclaim_zombies(session)
        await session.flush()
        drift_enqueued = await _enqueue_drift(session)
        await session.commit()
        return ReconcileStats(
            zombies_requeued=zombies_requeued,
            zombies_failed=zombies_failed,
            drift_enqueued=drift_enqueued,
        )
    except Exception:
        await session.rollback()
        raise
    finally:
        try:
            await _release_lock(session)
        except Exception:
            logger.exception("reconciler advisory unlock failed")


async def run_once() -> ReconcileStats:
    async with SessionLocal() as session:
        return await tick(session)


async def run_forever() -> None:
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
