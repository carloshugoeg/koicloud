from __future__ import annotations

import json

import httpx

from koicloud_cli.client import ApiClient
from koicloud_cli.commands.sql import HISTORY_QUERY_MAX_CHARS
from koicloud_cli.main import app


def test_sql_run_read_prints_table(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        assert request.headers["x-koi-surface"] == "cli"
        if request.url.path.endswith("/ponds/by-name/inventario"):
            return httpx.Response(
                200,
                json={"pond": {"id": "pond_sql", "name": "inventario"}},
            )
        assert request.method == "POST"
        assert request.url.path == "/api/v1/ponds/pond_sql/sql"
        body = json.loads(request.content.decode())
        assert body == {"query": "SELECT 1", "mode": "read"}
        return httpx.Response(
            200,
            json={
                "columns": ["?column?"],
                "rows": [[1]],
                "row_count": 1,
                "duration_ms": 4,
                "truncated": False,
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        ["sql", "run", "--pond", "inventario", "-q", "SELECT 1"],
    )

    assert result.exit_code == 0
    assert calls == [
        "GET /api/v1/ponds/by-name/inventario",
        "POST /api/v1/ponds/pond_sql/sql",
    ]
    assert "?column?" in result.output
    assert "1" in result.output
    assert "duración=4ms" in result.output
    assert "truncado=no" in result.output


def test_sql_run_write_proposes_without_executing(
    monkeypatch, runner, write_logged_in_config
) -> None:
    write_logged_in_config()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path.endswith("/ponds/by-name/inventario"):
            return httpx.Response(
                200,
                json={"pond": {"id": "pond_sql", "name": "inventario"}},
            )
        assert request.method == "POST"
        assert request.url.path == "/api/v1/ponds/pond_sql/sql"
        body = json.loads(request.content.decode())
        assert body == {"query": "DELETE FROM t", "mode": "write"}
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf-sql-write-abc",
                "summary": (
                    "Se ejecutará SQL en modo write sobre el pond 'pond_sql' "
                    "para demo@koicloud.dev. Expira en 5 min."
                ),
                "expires_at": "2026-10-18T21:05:00Z",
                "next": {"cli_example": "koicloud confirm conf-sql-write-abc"},
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        ["sql", "run", "--pond", "inventario", "-q", "DELETE FROM t", "--write"],
    )

    assert result.exit_code == 0
    assert calls == [
        "GET /api/v1/ponds/by-name/inventario",
        "POST /api/v1/ponds/pond_sql/sql",
    ]
    assert "POST /api/v1/confirm/" not in " ".join(calls)
    assert "modo write" in result.output
    assert "Token: conf-sql-write-abc" in result.output
    assert "koicloud confirm conf-sql-write-abc" in result.output


def test_sql_run_timeout_exits_nonzero(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ponds/by-name/lento"):
            return httpx.Response(
                200,
                json={"pond": {"id": "pond_slow", "name": "lento"}},
            )
        return httpx.Response(
            504,
            json={
                "code": "sql_timeout",
                "message": "La consulta excedió 10 s",
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        ["sql", "run", "--pond", "lento", "-q", "SELECT pg_sleep(30)"],
    )

    assert result.exit_code == 1
    assert "sql_timeout" in result.output
    assert "10 s" in result.output


def test_sql_run_client_read_timeout_exits_clean(
    monkeypatch, runner, write_logged_in_config
) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ponds/by-name/lento"):
            return httpx.Response(
                200,
                json={"pond": {"id": "pond_slow", "name": "lento"}},
            )
        raise httpx.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        ["sql", "run", "--pond", "lento", "-q", "SELECT pg_sleep(30)"],
    )

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "sql_timeout" in result.output
    assert "10 segundos" in result.output


def test_sql_run_yes_without_write_rejected(runner, write_logged_in_config) -> None:
    write_logged_in_config()
    result = runner.invoke(
        app,
        ["sql", "run", "--pond", "x", "-q", "SELECT 1", "--yes", "tok"],
    )
    assert result.exit_code == 1
    assert "--yes solo aplica con --write" in result.output


def test_sql_run_write_yes_confirms_token(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        assert request.method == "POST"
        assert request.url.path == "/api/v1/confirm/conf-sql-yes"
        return httpx.Response(
            200,
            json={
                "columns": ["ok"],
                "rows": [[True]],
                "row_count": 1,
                "duration_ms": 3,
                "truncated": False,
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        [
            "sql",
            "run",
            "--pond",
            "inventario",
            "-q",
            "DELETE FROM t",
            "--write",
            "--yes",
            "conf-sql-yes",
        ],
    )

    assert result.exit_code == 0
    assert calls == ["POST /api/v1/confirm/conf-sql-yes"]
    assert "ok" in result.output
    assert "duración=3ms" in result.output


def test_sql_history_lists_truncation_signal(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    long_query = "Q" * HISTORY_QUERY_MAX_CHARS

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ponds/by-name/inventario"):
            return httpx.Response(
                200,
                json={"pond": {"id": "pond_sql", "name": "inventario"}},
            )
        assert request.method == "GET"
        assert request.url.path == "/api/v1/ponds/pond_sql/sql/history"
        return httpx.Response(
            200,
            json={
                "events": [
                    {
                        "id": "evt_1",
                        "pond_id": "pond_sql",
                        "query_truncated": long_query,
                        "mode": "read",
                        "row_count": 1,
                        "duration_ms": 4,
                        "executed_at": "2026-10-18T20:00:00Z",
                    },
                    {
                        "id": "evt_2",
                        "pond_id": "pond_sql",
                        "query_truncated": "SELECT 2",
                        "mode": "read",
                        "row_count": 1,
                        "duration_ms": 2,
                        "executed_at": "2026-10-18T19:00:00Z",
                    },
                ],
                "next_cursor": None,
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["sql", "history", "--pond", "inventario"])

    assert result.exit_code == 0
    assert "Historial SQL" in result.output
    assert "Truncado" in result.output
    assert "sí" in result.output
    assert "SELECT 2" in result.output
    assert "no" in result.output


def test_sql_run_requires_login(runner) -> None:
    result = runner.invoke(app, ["sql", "run", "--pond", "x", "-q", "SELECT 1"])
    assert result.exit_code == 1
    assert "Primero corré `koicloud login`" in result.output
