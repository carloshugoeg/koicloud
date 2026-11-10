"""Phase-1 regressions for log/Sentry leak paths. Do not weaken these assertions."""

from __future__ import annotations

import logging
from uuid import uuid4

import pytest

from app.modules.jobs import failure as failure_mod
from app.modules.jobs.failure import redact, report_failure

ROW = "secret-row-value-koi-9c2e"
PASSWORD = "p@ss/word with spaces"
COPY_PAYLOAD = f"42\t{ROW}\tmore-data"


def _restore_stderr() -> str:
    return (
        f'psql:/tmp/restore.sql:12: ERROR:  duplicate key value violates unique constraint "alumnos_pkey"\n'
        f"DETAIL:  Failing row contains (42, {ROW}, more-data).\n"
        f"CONTEXT:  COPY alumnos, line 1\n"
        f"{COPY_PAYLOAD}\n"
        f"Key ({ROW}) already exists.\n"
        f"postgresql://postgres:{PASSWORD}@127.0.0.1:5432/demo\n"
        f"PGPASSWORD={PASSWORD}\n"
        f'{{"password": "{PASSWORD}"}}\n'
    )


def _dump_stderr() -> str:
    rows = "\n".join(f"{i}\t{ROW}-{i}" for i in range(200))
    return (
        "pg_dump: error: query failed: ERROR:  out of memory\n"
        f"DETAIL:  Failing row contains (1, {ROW}).\n"
        "CONTEXT:  COPY alumnos, line 1\n"
        f"{rows}\n"
        f"postgresql://postgres:{PASSWORD}@127.0.0.1:5432/demo\n"
        f"PGPASSWORD={PASSWORD}\n"
        f'{{"password": "{PASSWORD}"}}\n'
    )


def test_redact_drops_detail_context_key_and_tab_rows() -> None:
    out = redact(_restore_stderr())
    assert "DETAIL" not in out
    assert "CONTEXT" not in out
    assert "Key (" not in out
    assert ROW not in out
    assert COPY_PAYLOAD not in out
    assert "duplicate key" in out or "ERROR" in out


def test_redact_closes_password_regex_gaps() -> None:
    out = redact(_restore_stderr())
    assert PASSWORD not in out
    assert "p@ss" not in out
    assert "with spaces" not in out
    assert "PGPASSWORD=" not in out or "PGPASSWORD=[redacted]" in out
    assert f'"{PASSWORD}"' not in out
    assert "[redacted]" in out


def test_redact_caps_output_at_500_characters() -> None:
    out = redact(_dump_stderr())
    assert len(out) <= 500
    assert ROW not in out


def test_report_failure_log_keeps_only_pg_error_lines(
    caplog: pytest.LogCaptureFixture,
) -> None:
    job_id = uuid4()
    with caplog.at_level(logging.ERROR, logger=failure_mod.logger.name):
        report_failure(job_id, _restore_stderr())
    text = caplog.text
    assert "DETAIL" not in text
    assert "CONTEXT" not in text
    assert ROW not in text
    assert PASSWORD not in text
    assert "ERROR" in text
    logged = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == failure_mod.logger.name
    )
    assert len(logged) <= 500 + len(f"job {job_id} failed: ")


def test_sentry_receives_only_code_and_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    import inspect

    captured: list[str] = []

    monkeypatch.setenv("SENTRY_DSN", "https://key@127.0.0.1/1")

    class _FakeSentry:
        @staticmethod
        def is_initialized() -> bool:
            return True

        @staticmethod
        def init(**kwargs: object) -> None:
            _ = kwargs

        @staticmethod
        def capture_message(message: str, level: str | None = None) -> None:
            _ = level
            captured.append(message)

    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", _FakeSentry)

    job_id = uuid4()
    pond_id = uuid4()
    assert "pond_id" in inspect.signature(report_failure).parameters
    report_failure(job_id, _dump_stderr(), pond_id=pond_id)

    assert len(captured) == 1
    message = captured[0]
    assert len(message) <= 500
    assert str(job_id) in message
    assert str(pond_id) in message
    assert ROW not in message
    assert "DETAIL" not in message
    assert "CONTEXT" not in message
    assert PASSWORD not in message
    assert "out of memory" not in message
    assert "pg_dump" not in message


def test_sentry_sdk_inits_at_startup_without_logging_integration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inits: list[dict[str, object]] = []

    class _FakeSentry:
        @staticmethod
        def is_initialized() -> bool:
            return False

        @staticmethod
        def init(**kwargs: object) -> None:
            inits.append(kwargs)

    monkeypatch.setenv("SENTRY_DSN", "https://key@127.0.0.1/1")
    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", _FakeSentry)

    from app.core import sentry as sentry_mod

    monkeypatch.setattr(sentry_mod, "sentry_sdk", _FakeSentry)
    sentry_mod.init_sentry()

    assert len(inits) == 1
    kwargs = inits[0]
    assert kwargs.get("dsn") == "https://key@127.0.0.1/1"
    assert kwargs.get("default_integrations") is False
    assert kwargs.get("integrations") == []
    assert kwargs.get("send_default_pii") is False
