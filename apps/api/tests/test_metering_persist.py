from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.models import PondSample
from app.core.time import utc_now
from app.main import app
from app.modules.metering.service import compute_day_metrics
from app.workers.daily_usage import run as aggregate_usage_day
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


def _create_running_pond(name: str = "inventario-demo") -> tuple[dict[str, str], str]:
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
    return headers, pond_id


def _sample_count(pond_id: str) -> int:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM pond_samples WHERE pond_id = :pond_id"),
            {"pond_id": pond_id},
        ).scalar_one()
    engine.dispose()
    return int(count)


def _seed_samples_for_day(
    pond_id: str,
    day: date,
    *,
    size_bytes: int = 134_217_728,
) -> None:
    """Insert two running samples on ``day`` at 01:00 and 02:00 UTC."""
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    day_start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM pond_samples WHERE pond_id = :pond_id"),
            {"pond_id": pond_id},
        )
        for hour in (1, 2):
            connection.execute(
                text(
                    """
                    INSERT INTO pond_samples (id, pond_id, size_bytes, container_state, sampled_at)
                    VALUES (gen_random_uuid(), :pond_id, :size_bytes, 'running', :sampled_at)
                    """
                ),
                {
                    "pond_id": pond_id,
                    "size_bytes": size_bytes,
                    "sampled_at": day_start + timedelta(hours=hour),
                },
            )
    engine.dispose()


def test_get_usage_empty_zeros_not_fixture() -> None:
    reset_pond_tables()
    headers = auth_headers()
    response = client.get("/api/v1/usage", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_instance_hours"] == 0.0
    assert body["total_storage_gb_hours"] == 0.0
    assert body["ponds"] == []
    assert body["month"]  # current YYYY-MM


def test_ingest_samples_and_heartbeat_persist() -> None:
    headers, pond_id = _create_running_pond()

    posted = client.post(
        "/internal/v1/samples",
        headers=node_headers(),
        json=[
            {
                "pond_id": pond_id,
                "size_bytes": 42_000_000,
                "container_state": "running",
            }
        ],
    )
    assert posted.status_code == 200
    assert posted.json() == {"ok": True}
    assert _sample_count(pond_id) == 1

    beat = client.post(
        "/internal/v1/heartbeat",
        headers=node_headers(),
        json={
            "containers": [{"name": "pond-inventario-demo", "state": "running", "uptime": "1h"}],
            "samples": [
                {
                    "pond_name": "inventario-demo",
                    "size_bytes": 50_000_000,
                    "container_state": "running",
                }
            ],
        },
    )
    assert beat.status_code == 200
    assert beat.json() == {"ok": True}
    assert _sample_count(pond_id) == 2

    empty = client.get("/api/v1/usage", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["total_instance_hours"] == 0.0
    assert empty.json()["ponds"] == []


def test_aggregate_then_get_usage_reflects_storage_and_hours() -> None:
    headers, pond_id = _create_running_pond()

    # Stable calendar day (yesterday) so the run does not depend on wall-clock hour.
    day = utc_now().astimezone(UTC).date() - timedelta(days=1)
    _seed_samples_for_day(pond_id, day, size_bytes=134_217_728)

    upserted = asyncio.run(aggregate_usage_day(day))
    assert upserted == 1

    # Idempotent re-run
    assert asyncio.run(aggregate_usage_day(day)) == 1

    month = f"{day.year:04d}-{day.month:02d}"
    usage = client.get(f"/api/v1/usage?month={month}", headers=headers)
    assert usage.status_code == 200
    body = usage.json()
    assert body["month"] == month
    assert body["total_instance_hours"] > 0
    assert body["total_storage_gb_hours"] > 0
    assert len(body["ponds"]) == 1
    assert body["ponds"][0]["pond_id"] == pond_id
    assert body["ponds"][0]["pond_name"] == "inventario-demo"
    assert body["ponds"][0]["instance_hours"] > 0
    assert body["ponds"][0]["storage_gb_hours"] > 0


def test_compute_day_metrics_unit() -> None:
    day = date(2026, 10, 2)
    day_start = datetime(2026, 10, 2, 0, 0, tzinfo=UTC)
    samples = [
        PondSample(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            pond_id=UUID("66666666-6666-6666-6666-666666666666"),
            size_bytes=1024**3,  # 1 GiB
            container_state="running",
            sampled_at=day_start + timedelta(hours=1),
        ),
        PondSample(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            pond_id=UUID("66666666-6666-6666-6666-666666666666"),
            size_bytes=1024**3,
            container_state="stopped",
            sampled_at=day_start + timedelta(hours=3),
        ),
    ]
    # Window ends at 04:00 so tail after stopped does not add hours.
    now = day_start + timedelta(hours=4)
    instance_hours, storage = compute_day_metrics(samples, day=day, now=now)
    # 00–01 assume running + 01–03 running = 3h; 03–04 stopped = 0 → 3.0
    assert float(instance_hours) == 3.0
    # avg 1 GiB × 24h = 24
    assert float(storage) == 24.0
