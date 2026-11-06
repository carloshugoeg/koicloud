"""Phase-1 regressions for dump/restore outbound leaks. Do not weaken these assertions."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from agent.client import ClaimedJob, CompletionReport
from agent.drivers.base import PondDriverError, PondSpec
from agent.drivers.docker_driver import DockerDriver
from agent.drivers.mock_driver import MockDriver
from agent.main import run_once

ROW = "ROWDATA-koi-outbound-7f3a"
PASSWORD = "p@ss/word with spaces"


def build_backup_job(job_id: str = "job_backup_1") -> ClaimedJob:
    return ClaimedJob.model_validate(
        {
            "id": job_id,
            "type": "backup_pond",
            "pond_id": "pond_123",
            "payload": {"name": "demo", "backup_id": "bak_1"},
        }
    )


def build_restore_job(job_id: str = "job_restore_1") -> ClaimedJob:
    return ClaimedJob.model_validate(
        {
            "id": job_id,
            "type": "restore_pond",
            "pond_id": "pond_123",
            "payload": {"name": "demo", "backup_id": "bak_1"},
        }
    )


class FakeClient:
    def __init__(self, job: ClaimedJob | None) -> None:
        self.job = job
        self.completed: list[tuple[str, CompletionReport]] = []

    def claim_job(self) -> ClaimedJob | None:
        job, self.job = self.job, None
        return job

    def complete_job(self, job_id: str, report: CompletionReport) -> None:
        self.completed.append((job_id, report))


class DumpLeakDriver(MockDriver):
    def dump(self, pond_name: str, backup_id: str | None = None):  # type: ignore[override]
        _ = backup_id
        detail = (
            "pg_dump: error: query failed: ERROR:  out of memory\n"
            f"DETAIL:  Failing row contains (1, {ROW}).\n"
            "CONTEXT:  COPY alumnos, line 1\n"
            + "\n".join(f"{i}\t{ROW}-{i}" for i in range(50))
            + f"\npostgresql://postgres:{PASSWORD}@127.0.0.1:5432/demo\n"
        )
        raise PondDriverError(f"dump_failed:{pond_name}:{detail}")


class RestoreLeakDriver(MockDriver):
    def restore(self, pond_name: str, backup_id: str):  # type: ignore[override]
        _ = backup_id
        detail = (
            f'psql:/tmp/restore.sql:12: ERROR:  duplicate key value violates unique constraint "alumnos_pkey"\n'
            f"DETAIL:  Failing row contains (42, {ROW}, more).\n"
            f"CONTEXT:  COPY alumnos, line 1\n"
            f"42\t{ROW}\tmore\n"
            f"PGPASSWORD={PASSWORD}\n"
        )
        raise PondDriverError(f"restore_failed:{pond_name}:{detail}")


def test_dump_keeps_only_pg_dump_lines(tmp_path: Path) -> None:
    import importlib.util
    from pathlib import Path as PathType

    fake_path = PathType(__file__).resolve().parent / "test_docker_driver.py"
    spec = importlib.util.spec_from_file_location("job_error_dump_fakes", fake_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    client = module.FakeClient()
    driver = DockerDriver(
        client=client,
        backup_dir=tmp_path,
        public_host="127.0.0.1",
        ready_timeout_seconds=1.0,
    )
    driver.create_pond(module.build_spec("demo"))
    container = client.containers.get("koicloud-demo")

    def leaky_exec(cmd: list[str]) -> tuple[int, bytes]:
        if cmd and cmd[0] == "pg_dump":
            body = (
                b"pg_dump: error: query failed: ERROR:  out of memory\n"
                b"DETAIL:  Failing row contains (1, leak).\n"
                b"CONTEXT:  COPY alumnos, line 1\n"
                + b"\n".join(f"{i}\t{ROW}-{i}".encode() for i in range(300))
            )
            return 1, body
        return module.FakeContainer.exec_run(container, cmd)

    container.exec_run = leaky_exec  # type: ignore[method-assign]

    with pytest.raises(PondDriverError) as raised:
        driver.dump("demo", "bak_1")

    message = str(raised.value)
    assert ROW not in message
    assert "DETAIL" not in message
    assert "CONTEXT" not in message
    assert message.startswith("dump_failed:demo")
    assert "pg_dump:" in message
    for line in message.splitlines():
        if line.startswith("dump_failed:"):
            continue
        assert line.startswith("pg_dump:"), line
    assert len(message) <= 500


def test_run_once_sends_bare_code_and_job_id_on_dump_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeClient(build_backup_job("job_backup_1"))
    with caplog.at_level(logging.ERROR):
        assert run_once(client, DumpLeakDriver()) is True

    assert len(client.completed) == 1
    report = client.completed[0][1]
    assert report.status == "failed"
    assert report.error == "backup_failed:job_backup_1" or report.error == "dump_failed:job_backup_1"
    assert ROW not in (report.error or "")
    assert PASSWORD not in (report.error or "")
    assert "DETAIL" not in caplog.text
    assert "CONTEXT" not in caplog.text
    assert ROW not in caplog.text
    assert PASSWORD not in caplog.text
    assert len(caplog.text) < 4000


def test_run_once_sends_bare_code_and_job_id_on_restore_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeClient(build_restore_job("job_restore_1"))
    with caplog.at_level(logging.ERROR):
        assert run_once(client, RestoreLeakDriver()) is True

    report = client.completed[0][1]
    assert report.status == "failed"
    assert report.error == "restore_failed:job_restore_1"
    assert ROW not in (report.error or "")
    assert "DETAIL" not in caplog.text
    assert "CONTEXT" not in caplog.text
    assert ROW not in caplog.text
