from __future__ import annotations

import importlib.util
import io
import logging
import sys
import tarfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

_AGENT_ROOT = Path(__file__).resolve().parents[3] / "apps" / "node-agent"
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

client = TestClient(app)

ROW = "ROWVALUE-koi-7f3a"
PASSWORD = "SuperSecretPondPw"
PSQL_LINE = 'psql:/tmp/restore.sql:2: ERROR:  syntax error at or near "BROKEN"'
RESTORE_PUBLIC = "restore_failed: No se pudo restaurar el pond."
BACKUP_PUBLIC = "backup_failed: No se pudo crear el respaldo."
CREATE_PUBLIC = "create_failed: No se pudo crear el pond."
STALE_PUBLIC = "job_failed: No se pudo completar la operación."


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


def _execute(statement: str, params: dict[str, object]) -> None:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as db:
        db.execute(text(statement), params)
    engine.dispose()


def _running_pond(name: str) -> tuple[dict[str, str], str, str]:
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
    return headers, pond_id, job_id


def _fakes():
    fake_path = _AGENT_ROOT / "tests" / "test_docker_driver.py"
    spec = importlib.util.spec_from_file_location("job_error_docker_fakes", fake_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _untar(data: bytes) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as archive:
        member = archive.next()
        if member is None:
            return b""
        extracted = archive.extractfile(member)
        if extracted is None:
            return b""
        return extracted.read()


def _driver(tmp_path: Path, *, leak_psql: bool, leak_dump: bool):
    from agent.drivers.docker_driver import DockerDriver

    module = _fakes()
    original_exec = module.FakeContainer.exec_run
    original_put = module.FakeContainer.put_archive

    def exec_run(
        self, cmd: list[str], environment: dict[str, str] | None = None, **kwargs: object
    ) -> tuple[int, bytes]:
        if leak_psql and cmd and cmd[0] == "psql":
            dumped = getattr(self, "dumped", b"")
            detail = (
                f"{PSQL_LINE}\n{dumped.decode()}\n"
                f"postgresql://postgres:{PASSWORD}@127.0.0.1:5432/demo\n"
            )
            return 1, detail.encode()
        if leak_dump and cmd and cmd[0] == "pg_dump":
            detail = (
                f"{PSQL_LINE}\nINSERT INTO alumnos (nombre) VALUES ('{ROW}');\n"
                f"postgresql://postgres:{PASSWORD}@127.0.0.1:5432/demo\n"
            )
            return 1, detail.encode()
        return original_exec(self, cmd, environment=environment, **kwargs)

    def put_archive(self, path: str, data: bytes) -> bool:
        self.dumped = _untar(data)
        return original_put(self, path, data)

    module.FakeContainer.exec_run = exec_run
    module.FakeContainer.put_archive = put_archive
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


def _read_job(headers: dict[str, str], pond_id: str, job_id: str) -> tuple[dict[str, object], str]:
    response = client.get(f"/api/v1/ponds/{pond_id}/jobs/{job_id}", headers=headers)
    assert response.status_code == 200
    return response.json()["job"], response.text


def _assert_public(job: dict[str, object], raw_response: str, expected: str) -> None:
    assert job["status"] == "failed"
    assert job["last_error"] == expected
    assert ROW not in raw_response
    assert PASSWORD not in raw_response
    assert "psql" not in raw_response.lower()
    assert "INSERT" not in raw_response


def _assert_server_log(caplog: pytest.LogCaptureFixture) -> None:
    text = caplog.text
    assert "syntax error" in text
    assert ROW not in text
    assert PASSWORD not in text


def test_failed_restore_of_a_dump_hides_row_data(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from agent.drivers.base import PondSpec
    from agent.main import run_once

    name = "restore-leak"
    headers, pond_id, _job_id = _running_pond(name)
    plain = _driver(tmp_path, leak_psql=False, leak_dump=False)
    plain.create_pond(
        PondSpec(
            pond_id=pond_id,
            name=name,
            host_port=15021,
            memory_mb=512,
            cpus=0.5,
            db_password_plain="pond-secret",
        )
    )
    triggered = client.post(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert triggered.status_code == 202
    backup_id = triggered.json()["backup"]["id"]
    backup_job = triggered.json()["job"]["id"]
    plain.dump(name, backup_id)
    claimed = client.post("/internal/v1/jobs/claim", headers=_node_headers(), json={})
    assert claimed.status_code == 200
    done = client.post(
        f"/internal/v1/jobs/{backup_job}/complete",
        headers=_node_headers(),
        json={
            "status": "succeeded",
            "result": {
                "backup": {
                    "path": str(tmp_path / f"{name}-{backup_id}.sql"),
                    "size_bytes": 12,
                    "sha256": "ab" * 32,
                }
            },
        },
    )
    assert done.status_code == 204
    dump = tmp_path / f"{name}-{backup_id}.sql"
    dump.write_text(f"INSERT INTO alumnos (nombre) VALUES ('{ROW}');\nBROKEN\n", encoding="utf-8")

    restored = client.post(
        f"/api/v1/ponds/{pond_id}/restore",
        headers=headers,
        json={"backup_id": backup_id},
    )
    assert restored.status_code == 202
    job_id = restored.json()["job"]["id"]
    leaky = _driver(tmp_path, leak_psql=True, leak_dump=False)
    leaky.create_pond(
        PondSpec(
            pond_id=pond_id,
            name=name,
            host_port=15021,
            memory_mb=512,
            cpus=0.5,
            db_password_plain="pond-secret",
        )
    )
    with caplog.at_level(logging.INFO):
        assert run_once(_agent(), leaky) is True

    job, raw = _read_job(headers, pond_id, job_id)
    _assert_public(job, raw, RESTORE_PUBLIC)
    _assert_server_log(caplog)


def test_failed_backup_hides_command_output(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from agent.drivers.base import PondSpec
    from agent.main import run_once

    name = "backup-leak"
    headers, pond_id, _job_id = _running_pond(name)
    driver = _driver(tmp_path, leak_psql=False, leak_dump=True)
    driver.create_pond(
        PondSpec(
            pond_id=pond_id,
            name=name,
            host_port=15022,
            memory_mb=512,
            cpus=0.5,
            db_password_plain="pond-secret",
        )
    )
    triggered = client.post(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert triggered.status_code == 202
    job_id = triggered.json()["job"]["id"]
    with caplog.at_level(logging.INFO):
        assert run_once(_agent(), driver) is True

    job, raw = _read_job(headers, pond_id, job_id)
    _assert_public(job, raw, BACKUP_PUBLIC)
    _assert_server_log(caplog)


def test_node_agent_reported_failure_hides_command_output(caplog: pytest.LogCaptureFixture) -> None:
    reset_pond_tables()
    headers = _headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": "agent-leak"})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]
    job_id = created.json()["job"]["id"]
    claimed = client.post("/internal/v1/jobs/claim", headers=_node_headers(), json={})
    assert claimed.status_code == 200
    raw_error = (
        f"{PSQL_LINE}\nINSERT INTO alumnos (nombre) VALUES ('{ROW}');\n"
        f"postgresql://postgres:{PASSWORD}@127.0.0.1:5432/demo\n"
    )
    with caplog.at_level(logging.INFO):
        done = client.post(
            f"/internal/v1/jobs/{job_id}/complete",
            headers=_node_headers(),
            json={"status": "failed", "error": raw_error},
        )
    assert done.status_code == 204
    job, raw = _read_job(headers, pond_id, job_id)
    _assert_public(job, raw, CREATE_PUBLIC)
    _assert_server_log(caplog)


def test_existing_job_row_is_not_returned_raw() -> None:
    headers, pond_id, job_id = _running_pond("stale-leak")
    stored = (
        f"{PSQL_LINE}\nINSERT INTO alumnos (nombre) VALUES ('{ROW}');\n"
        f"postgresql://postgres:{PASSWORD}@127.0.0.1:5432/demo\n"
    )
    _execute(
        "UPDATE jobs SET last_error = :error WHERE id = :job_id",
        {"error": stored, "job_id": job_id},
    )
    job, raw = _read_job(headers, pond_id, job_id)
    assert job["last_error"] == STALE_PUBLIC
    assert ROW not in raw
    assert PASSWORD not in raw
    assert "psql" not in raw.lower()
    assert "INSERT" not in raw
