from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import JobStatus, JobType, PondObservedState
from app.core.models import Job, PondStatus
from app.core.time import utc_now
from app.main import app
from app.workers.reconciler import MAX_ATTEMPTS, tick
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def node_headers() -> dict[str, str]:
    return {"X-Node-Token": get_settings().node_token}


def _create_and_complete_pond(name: str = "inventario-demo") -> str:
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": name})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]
    job_id = created.json()["job"]["id"]

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=node_headers(),
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204
    return pond_id


async def _run_tick():
    async with SessionLocal() as session:
        stats = await tick(session)
        await session.commit()
        return stats


def test_reconciler_enqueues_start_pond_on_stopped_drift() -> None:
    pond_id = _create_and_complete_pond()

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.STOPPED
            status.healthy = False
            await session.commit()
        return await _run_tick()

    stats = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 1
    assert stats.skipped_lock is False

    async def read_jobs():
        async with SessionLocal() as session:
            jobs = (
                await session.scalars(
                    select(Job)
                    .where(Job.pond_id == UUID(pond_id), Job.status == JobStatus.QUEUED)
                    .order_by(Job.created_at.desc())
                )
            ).all()
            return jobs

    jobs = asyncio.run(read_jobs())
    assert len(jobs) == 1
    assert jobs[0].type == JobType.START_POND
    assert jobs[0].payload["name"] == "inventario-demo"


def test_reconciler_skips_when_active_job_exists() -> None:
    pond_id = _create_and_complete_pond()

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.STOPPED
            pond_job = Job(
                type=JobType.START_POND,
                pond_id=UUID(pond_id),
                node_id=get_settings().node_id,
                status=JobStatus.QUEUED,
                payload={"name": "inventario-demo"},
            )
            session.add(pond_job)
            await session.commit()
        return await _run_tick()

    stats = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 0

    async def count_queued():
        async with SessionLocal() as session:
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                        Job.type == JobType.START_POND,
                    )
                )
            ).all()
            return len(jobs)

    assert asyncio.run(count_queued()) == 1


def test_reconciler_requeues_zombie_running_job() -> None:
    pond_id = _create_and_complete_pond("zombie-demo")
    # Leave desired=running / observed=running; seed a stale RUNNING job.
    async def setup_and_tick():
        async with SessionLocal() as session:
            job = Job(
                type=JobType.START_POND,
                pond_id=UUID(pond_id),
                node_id=get_settings().node_id,
                status=JobStatus.RUNNING,
                payload={"name": "zombie-demo"},
                attempts=1,
                claimed_at=utc_now() - timedelta(minutes=5),
            )
            session.add(job)
            await session.commit()
            job_id = job.id
        stats = await _run_tick()
        return stats, job_id

    stats, job_id = asyncio.run(setup_and_tick())
    assert stats.zombies_requeued == 1

    async def read_job():
        async with SessionLocal() as session:
            return await session.get(Job, job_id)

    job = asyncio.run(read_job())
    assert job is not None
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 2
    assert job.claimed_at is None


def test_reconciler_fails_zombie_at_max_attempts() -> None:
    pond_id = _create_and_complete_pond("zombie-max")

    async def setup_and_tick():
        async with SessionLocal() as session:
            job = Job(
                type=JobType.CREATE_POND,
                pond_id=UUID(pond_id),
                node_id=get_settings().node_id,
                status=JobStatus.RUNNING,
                payload={"name": "zombie-max"},
                attempts=MAX_ATTEMPTS - 1,
                claimed_at=utc_now() - timedelta(minutes=5),
            )
            session.add(job)
            await session.commit()
            job_id = job.id
        stats = await _run_tick()
        return stats, job_id

    stats, job_id = asyncio.run(setup_and_tick())
    assert stats.zombies_failed == 1
    assert stats.zombies_requeued == 0

    async def read_job():
        async with SessionLocal() as session:
            return await session.get(Job, job_id)

    job = asyncio.run(read_job())
    assert job is not None
    assert job.status == JobStatus.FAILED
    assert job.attempts == MAX_ATTEMPTS


def test_reconciler_skips_non_remediable_pair() -> None:
    pond_id = _create_and_complete_pond("restore-demo")

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.RESTORING
            await session.commit()
        return await _run_tick()

    stats = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 0

    async def count_queued():
        async with SessionLocal() as session:
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return len(jobs)

    assert asyncio.run(count_queued()) == 0


def test_reconciler_skips_exhausted_failed_create() -> None:
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": "exhausted-demo"})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]
    job_id = created.json()["job"]["id"]

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    failed = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=node_headers(),
        json={"status": "failed", "error": "boom"},
    )
    assert failed.status_code == 204

    async def mark_exhausted_and_tick():
        async with SessionLocal() as session:
            job = await session.get(Job, UUID(job_id))
            assert job is not None
            job.attempts = MAX_ATTEMPTS
            job.status = JobStatus.FAILED
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.FAILED
            await session.commit()
        return await _run_tick()

    stats = asyncio.run(mark_exhausted_and_tick())
    assert stats.drift_enqueued == 0
