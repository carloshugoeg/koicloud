from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import JobStatus, JobType, PondDesiredState, PondObservedState
from app.core.models import Job, Pond, PondStatus
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


def test_reconciler_enqueues_start_pond_on_stopped_drift() -> None:
    pond_id = _create_and_complete_pond()

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            pond = await session.get(Pond, UUID(pond_id))
            assert status is not None
            assert pond is not None
            status.observed_state = PondObservedState.STOPPED
            status.healthy = False
            await session.commit()
            host_port = pond.host_port

        async with SessionLocal() as session:
            stats = await tick(session)
            again = await tick(session)
            jobs = (
                await session.scalars(
                    select(Job)
                    .where(Job.pond_id == UUID(pond_id), Job.status == JobStatus.QUEUED)
                    .order_by(Job.created_at.desc())
                )
            ).all()
            pond = await session.get(Pond, UUID(pond_id))
            status = await session.get(PondStatus, UUID(pond_id))
            return stats, again, jobs, pond, status, host_port

    stats, again, jobs, pond, status, host_port = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 1
    assert stats.skipped_lock is False
    assert again.drift_enqueued == 0
    assert len(jobs) == 1
    assert jobs[0].type == JobType.START_POND
    assert jobs[0].attempts == 0
    assert jobs[0].payload["name"] == "inventario-demo"
    assert jobs[0].payload["host_port"] == host_port
    assert jobs[0].payload["db_password_plain"]
    assert jobs[0].payload["memory_mb"] == 512
    assert jobs[0].payload["cpus"] == 0.5
    assert jobs[0].payload["image"] == "postgres:16-alpine"
    assert pond is not None
    assert status is not None
    assert pond.desired_state == PondDesiredState.RUNNING
    assert status.observed_state == PondObservedState.STOPPED

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    body = claimed.json()["job"]
    assert body["type"] == "start_pond"
    assert body["payload"]["name"] == "inventario-demo"
    assert body["payload"]["db_password_plain"]

    done = client.post(
        f"/internal/v1/jobs/{body['id']}/complete",
        headers=node_headers(),
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204
    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=auth_headers())
    assert detail.status_code == 200
    assert detail.json()["pond"]["observed_state"] == "running"
    assert detail.json()["pond"]["desired_state"] == "running"


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

        async with SessionLocal() as session:
            return await tick(session)

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

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.STOPPED
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

        async with SessionLocal() as session:
            stats = await tick(session)
            again = await tick(session)
            job = await session.get(Job, job_id)
            queued = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, again, job, queued

    stats, again, job, queued = asyncio.run(setup_and_tick())
    assert stats.zombies_requeued == 1
    assert stats.drift_enqueued == 0
    assert again.zombies_requeued == 0
    assert again.drift_enqueued == 0
    assert job is not None
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 2
    assert job.claimed_at is None
    assert job.node_id is None
    assert len(queued) == 1
    assert queued[0].id == job.id


def test_reconciler_fails_zombie_at_max_attempts() -> None:
    pond_id = _create_and_complete_pond("zombie-max")

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.STOPPED
            job = Job(
                type=JobType.START_POND,
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

        async with SessionLocal() as session:
            stats = await tick(session)
            job = await session.get(Job, job_id)
            queued = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, job, queued

    stats, job, queued = asyncio.run(setup_and_tick())
    assert stats.zombies_failed == 1
    assert stats.zombies_requeued == 0
    assert stats.drift_enqueued == 0
    assert job is not None
    assert job.status == JobStatus.FAILED
    assert job.attempts == MAX_ATTEMPTS
    assert queued == []


def test_reconciler_skips_non_remediable_pair() -> None:
    pond_id = _create_and_complete_pond("restore-demo")

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.RESTORING
            await session.commit()

        async with SessionLocal() as session:
            stats = await tick(session)
            queued = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            pond = await session.get(Pond, UUID(pond_id))
            status = await session.get(PondStatus, UUID(pond_id))
            return stats, queued, pond, status

    stats, queued, pond, status = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 0
    assert queued == []
    assert pond is not None
    assert status is not None
    assert pond.desired_state == PondDesiredState.RUNNING
    assert status.observed_state == PondObservedState.RESTORING


async def _tick():
    async with SessionLocal() as session:
        return await tick(session)


def test_reconciler_stops_after_three_failed_claims() -> None:
    """Drift carries attempts so claim→fail→tick cannot loop forever."""
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": "exhausted-demo"})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]

    for _ in range(MAX_ATTEMPTS):
        claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
        assert claimed.status_code == 200
        job_id = claimed.json()["job"]["id"]
        failed = client.post(
            f"/internal/v1/jobs/{job_id}/complete",
            headers=node_headers(),
            json={"status": "failed", "error": "boom"},
        )
        assert failed.status_code == 204
        stats = asyncio.run(_tick())
        # After attempts 1 and 2, drift requeues. After 3, it stops.
        async def read_attempts(jid: str = job_id):
            async with SessionLocal() as session:
                job = await session.get(Job, UUID(jid))
                assert job is not None
                return job.attempts

        attempts = asyncio.run(read_attempts())
        if attempts < MAX_ATTEMPTS:
            assert stats.drift_enqueued == 1
        else:
            assert stats.drift_enqueued == 0

    async def count_queued():
        async with SessionLocal() as session:
            return len(
                (
                    await session.scalars(
                        select(Job).where(
                            Job.pond_id == UUID(pond_id),
                            Job.status == JobStatus.QUEUED,
                        )
                    )
                ).all()
            )

    assert asyncio.run(count_queued()) == 0


def test_reconciler_skips_deleted_running_without_pre_delete() -> None:
    """desired=deleted + observed=running needs pre_delete; reconciler no-ops."""
    pond_id = _create_and_complete_pond("delete-drift")

    async def setup_and_tick():
        async with SessionLocal() as session:
            pond = await session.get(Pond, UUID(pond_id))
            status = await session.get(PondStatus, UUID(pond_id))
            assert pond is not None
            assert status is not None
            pond.desired_state = PondDesiredState.DELETED
            status.observed_state = PondObservedState.RUNNING
            await session.commit()

        async with SessionLocal() as session:
            stats = await tick(session)
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, jobs

    stats, jobs = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 0
    assert jobs == []


def test_reconciler_skips_deleted_stopped_without_pre_delete() -> None:
    """desired=deleted + observed=stopped also needs pre_delete; reconciler no-ops."""
    pond_id = _create_and_complete_pond("delete-stopped")

    async def setup_and_tick():
        async with SessionLocal() as session:
            pond = await session.get(Pond, UUID(pond_id))
            status = await session.get(PondStatus, UUID(pond_id))
            assert pond is not None
            assert status is not None
            pond.desired_state = PondDesiredState.DELETED
            status.observed_state = PondObservedState.STOPPED
            await session.commit()

        async with SessionLocal() as session:
            stats = await tick(session)
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, jobs

    stats, jobs = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 0
    assert jobs == []


def test_reconciler_retries_failed_start_pond_on_running_failed() -> None:
    """_resolve_job_type keeps last failed start_pond instead of always create_pond."""
    pond_id = _create_and_complete_pond("start-retry")

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            pond = await session.get(Pond, UUID(pond_id))
            assert status is not None
            assert pond is not None
            status.observed_state = PondObservedState.FAILED
            session.add(
                Job(
                    type=JobType.START_POND,
                    pond_id=UUID(pond_id),
                    node_id=get_settings().node_id,
                    status=JobStatus.FAILED,
                    payload={
                        "name": "start-retry",
                        "host_port": pond.host_port,
                        "memory_mb": 512,
                        "cpus": 0.5,
                        "db_password_plain": "x",
                        "image": "postgres:16-alpine",
                    },
                    attempts=1,
                )
            )
            await session.commit()

        async with SessionLocal() as session:
            stats = await tick(session)
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, jobs

    stats, jobs = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 1
    assert len(jobs) == 1
    assert jobs[0].type == JobType.START_POND
    assert jobs[0].attempts == 1


def test_reconciler_holds_deleting_after_failed_backup() -> None:
    """Failed pre_delete backup must not unlock delete_pond via drift."""
    pond_id = _create_and_complete_pond("delete-backup-fail")

    async def setup_and_tick():
        async with SessionLocal() as session:
            pond = await session.get(Pond, UUID(pond_id))
            status = await session.get(PondStatus, UUID(pond_id))
            assert pond is not None
            assert status is not None
            pond.desired_state = PondDesiredState.DELETED
            status.observed_state = PondObservedState.DELETING
            session.add(
                Job(
                    type=JobType.BACKUP_POND,
                    pond_id=UUID(pond_id),
                    node_id=get_settings().node_id,
                    status=JobStatus.FAILED,
                    payload={"name": "delete-backup-fail"},
                    attempts=1,
                )
            )
            await session.commit()

        async with SessionLocal() as session:
            stats = await tick(session)
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, jobs

    stats, jobs = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 0
    assert jobs == []


def test_reconciler_retries_failed_delete_pond_while_deleting() -> None:
    """Only a failed delete_pond (not backup) may requeue while deleting."""
    pond_id = _create_and_complete_pond("delete-retry")

    async def setup_and_tick():
        async with SessionLocal() as session:
            pond = await session.get(Pond, UUID(pond_id))
            status = await session.get(PondStatus, UUID(pond_id))
            assert pond is not None
            assert status is not None
            pond.desired_state = PondDesiredState.DELETED
            status.observed_state = PondObservedState.DELETING
            session.add(
                Job(
                    type=JobType.DELETE_POND,
                    pond_id=UUID(pond_id),
                    node_id=get_settings().node_id,
                    status=JobStatus.FAILED,
                    payload={
                        "name": "delete-retry",
                        "host_port": pond.host_port,
                        "memory_mb": 512,
                        "cpus": 0.5,
                        "db_password_plain": "x",
                        "image": "postgres:16-alpine",
                    },
                    attempts=1,
                )
            )
            await session.commit()

        async with SessionLocal() as session:
            stats = await tick(session)
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, jobs

    stats, jobs = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 1
    assert len(jobs) == 1
    assert jobs[0].type == JobType.DELETE_POND
    assert jobs[0].attempts == 1
    assert jobs[0].payload["name"] == "delete-retry"


def test_reconciler_failed_does_not_replay_restore() -> None:
    """running+failed remediates create/start/delete only — never restore/backup."""
    pond_id = _create_and_complete_pond("restore-replay")

    async def setup_and_tick():
        async with SessionLocal() as session:
            status = await session.get(PondStatus, UUID(pond_id))
            assert status is not None
            status.observed_state = PondObservedState.FAILED
            session.add(
                Job(
                    type=JobType.RESTORE_POND,
                    pond_id=UUID(pond_id),
                    node_id=get_settings().node_id,
                    status=JobStatus.FAILED,
                    payload={"name": "restore-replay"},
                    attempts=1,
                )
            )
            await session.commit()

        async with SessionLocal() as session:
            stats = await tick(session)
            jobs = (
                await session.scalars(
                    select(Job).where(
                        Job.pond_id == UUID(pond_id),
                        Job.status == JobStatus.QUEUED,
                    )
                )
            ).all()
            return stats, jobs

    stats, jobs = asyncio.run(setup_and_tick())
    assert stats.drift_enqueued == 1
    assert len(jobs) == 1
    assert jobs[0].type == JobType.CREATE_POND
    assert jobs[0].type != JobType.RESTORE_POND
