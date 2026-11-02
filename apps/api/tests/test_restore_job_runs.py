from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

_AGENT_ROOT = Path(__file__).resolve().parents[3] / "apps" / "node-agent"
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

client = TestClient(app)


class _Transport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        headers = {key: value for key, value in request.headers.items() if key.lower() != "host"}
        response = client.request(
            request.method,
            request.url.path,
            content=request.content,
            headers=headers,
        )
        return httpx.Response(response.status_code, content=response.content)


def _headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _node_headers() -> dict[str, str]:
    return {"X-Node-Token": get_settings().node_token}


def _running_pond(name: str) -> tuple[dict[str, str], str]:
    reset_pond_tables()
    headers = _headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": name})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]
    job_id = created.json()["job"]["id"]
    claimed = client.post("/internal/v1/jobs/claim", headers=_node_headers(), json={})
    assert claimed.status_code == 200
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=_node_headers(),
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204
    return headers, pond_id


def _driver(tmp_path: Path):
    from agent.drivers.docker_driver import DockerDriver

    fake_path = _AGENT_ROOT / "tests" / "test_docker_driver.py"
    fake_path = _AGENT_ROOT / "tests" / "test_docker_driver.py"
    spec = importlib.util.spec_from_file_location("node_agent_docker_fakes", fake_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return DockerDriver(client=module.FakeClient(), backup_dir=tmp_path, public_host="127.0.0.1")


def _agent():
    from agent.client import InternalClient

    settings = get_settings()
    return InternalClient(
        base_url="http://test/internal/v1",
        node_token=settings.node_token,
        node_id=settings.node_id,
        transport=_Transport(),
    )


def _succeeded_backup(headers: dict[str, str], pond_id: str, driver, name: str) -> str:
    from agent.drivers.base import PondSpec
    triggered = client.post(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert triggered.status_code == 202
    backup_id = triggered.json()["backup"]["id"]
    job_id = triggered.json()["job"]["id"]
    driver.create_pond(
        PondSpec(
            pond_id=pond_id,
            name=name,
            host_port=15011,
            memory_mb=512,
            cpus=0.5,
            db_password_plain="pond-secret",
        )
    )
    driver.dump(name, backup_id)
    claimed = client.post("/internal/v1/jobs/claim", headers=_node_headers(), json={})
    assert claimed.status_code == 200
    assert claimed.json()["job"]["id"] == job_id
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=_node_headers(),
        json={
            "status": "succeeded",
            "result": {"backup": {"path": str(driver.backup_dir / f"{name}-{backup_id}.sql"), "size_bytes": 12, "sha256": "ab" * 32}},
        },
    )
    assert done.status_code == 204
    return str(backup_id)


def _enqueue_restore(headers: dict[str, str], pond_id: str, backup_id: str) -> str:
    restored = client.post(
        f"/api/v1/ponds/{pond_id}/restore",
        headers=headers,
        json={"backup_id": backup_id},
    )
    assert restored.status_code == 202
    job = restored.json()["job"]
    assert job["type"] == "restore_pond"
    assert job["status"] == "queued"
    return str(job["id"])


def test_restore_job_reaches_succeeded_on_docker_agent(tmp_path: Path) -> None:
    name = "demo-pond"
    headers, pond_id = _running_pond(name)
    driver = _driver(tmp_path)
    backup_id = _succeeded_backup(headers, pond_id, driver, name)
    job_id = _enqueue_restore(headers, pond_id, backup_id)

    from agent.main import run_once

    assert run_once(_agent(), driver) is True

    pond = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert pond.status_code == 200
    assert pond.json()["pond"]["observed_state"] == "running"
    assert pond.json()["pond"]["last_restore_at"] is not None

    listed = client.get(f"/api/v1/ponds/{pond_id}/jobs/{job_id}", headers=headers)
    assert listed.status_code == 200
    body = listed.json()["job"]
    assert body["id"] == job_id
    assert body["status"] == "succeeded"
    assert body["last_error"] is None


def test_restore_job_fails_when_backup_file_is_missing(tmp_path: Path) -> None:
    name = "demo-pond"
    headers, pond_id = _running_pond(name)
    driver = _driver(tmp_path)
    backup_id = _succeeded_backup(headers, pond_id, driver, name)
    dump = tmp_path / f"{name}-{backup_id}.sql"
    dump.unlink()
    job_id = _enqueue_restore(headers, pond_id, backup_id)

    from agent.main import run_once

    assert run_once(_agent(), driver) is True

    pond = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert pond.status_code == 200
    assert pond.json()["pond"]["observed_state"] == "failed"
    assert "backup_not_found" in (pond.json()["pond"]["last_error"] or "")

    listed = client.get(f"/api/v1/ponds/{pond_id}/jobs/{job_id}", headers=headers)
    assert listed.status_code == 200
    body = listed.json()["job"]
    assert body["status"] == "failed"
    assert "backup_not_found" in (body["last_error"] or "")
