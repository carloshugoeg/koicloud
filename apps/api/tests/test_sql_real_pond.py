"""SQL console against a real pond database, not the OpenAPI example."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import create_engine, text

from app.commands.sql import run_sql
from app.core.auth import AuthContext
from app.core.config import get_settings, to_sync_database_url
from app.core.enums import AppSurface, SQLMode, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.main import app
from app.schemas import RunSQLRequest, SQLResultResponse
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD
from tests.sql_probe_pond import (
    PROBE_DATABASE,
    PROBE_QUERY,
    PROBE_VALUE,
    probe_values,
    seed_probe_pond,
)

WRITE_INSERT = "INSERT INTO probe (n) VALUES (7)"
SQL_ERROR_MESSAGE = (
    "No se pudo ejecutar la consulta. Revisa la sintaxis, la tabla o los permisos."
)
CONSOLE_ROLE = "koi_console"
COPY_MARKER = "/tmp/koicloud-copy-program-marker"
COPY_PROGRAM = f"COPY (SELECT 1) TO PROGRAM 'touch {COPY_MARKER}'"
ROL_SUPER = "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
SERVER_FILE_MEMBER = (
    "SELECT ("
    "pg_has_role(current_user, 'pg_read_server_files', 'member') "
    "OR pg_has_role(current_user, 'pg_write_server_files', 'member') "
    "OR pg_has_role(current_user, 'pg_execute_server_program', 'member')"
    ") AS member_of_server_file_roles"
)
OWNS_APP = (
    "SELECT EXISTS ("
    "SELECT 1 FROM pg_namespace AS n "
    "JOIN pg_roles AS r ON r.oid = n.nspowner "
    "WHERE n.nspname = 'app' AND r.rolname = current_user"
    ") AS owns_app"
)

client = TestClient(app)


def _actor(user_id) -> AuthContext:
    return AuthContext(
        user_id=str(user_id),
        email=DEMO_EMAIL,
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.WEB,
    )


def _headers() -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_run_sql_read_returns_rows_from_the_real_pond() -> None:
    pond = seed_probe_pond()
    result = await run_sql(
        pond.pond_id,
        RunSQLRequest(query=PROBE_QUERY, mode=SQLMode.READ),
        actor=_actor(pond.user_id),
        surface=AppSurface.WEB,
    )

    assert isinstance(result, SQLResultResponse)
    assert result.columns == ["n"]
    assert result.rows == [[PROBE_VALUE]]
    assert result.row_count == 1
    assert result.truncated is False


async def test_run_sql_read_mode_rejects_writes() -> None:
    pond = seed_probe_pond()
    with pytest.raises(AppError) as raised:
        await run_sql(
            pond.pond_id,
            RunSQLRequest(query="INSERT INTO probe (n) VALUES (7)", mode=SQLMode.READ),
            actor=_actor(pond.user_id),
            surface=AppSurface.WEB,
        )

    assert raised.value.code == ErrorCode.SQL_READONLY_VIOLATION
    assert probe_values() == [PROBE_VALUE]


def test_sql_endpoint_returns_pond_rows_and_history() -> None:
    pond = seed_probe_pond()
    headers = _headers()
    response = client.post(
        f"/api/v1/ponds/{pond.pond_id}/sql",
        headers=headers,
        json={"query": PROBE_QUERY, "mode": "read"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["n"]
    assert body["rows"] == [[PROBE_VALUE]]
    assert body["row_count"] == 1
    assert body["truncated"] is False

    history = client.get(f"/api/v1/ponds/{pond.pond_id}/sql/history", headers=headers)
    assert history.status_code == 200
    queries = [event["query_truncated"] for event in history.json()["events"]]
    assert PROBE_QUERY in queries


def test_sql_endpoint_read_mode_rejects_writes() -> None:
    pond = seed_probe_pond()
    response = client.post(
        f"/api/v1/ponds/{pond.pond_id}/sql",
        headers=_headers(),
        json={"query": "INSERT INTO probe (n) VALUES (7)", "mode": "read"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "sql_readonly_violation"
    assert probe_values() == [PROBE_VALUE]


def _history_queries(pond_id, headers: dict[str, str]) -> list[str]:
    history = client.get(f"/api/v1/ponds/{pond_id}/sql/history", headers=headers)
    assert history.status_code == 200
    return [event["query_truncated"] for event in history.json()["events"]]


def test_sql_endpoint_write_insert_without_returning() -> None:
    pond = seed_probe_pond()
    headers = _headers()
    response = client.post(
        f"/api/v1/ponds/{pond.pond_id}/sql",
        headers=headers,
        json={"query": WRITE_INSERT, "mode": "write"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["columns"] == []
    assert body["rows"] == []
    assert isinstance(body["row_count"], int)
    assert body["truncated"] is False
    assert 7 in probe_values()
    assert WRITE_INSERT in _history_queries(pond.pond_id, headers)


def _close_stopped_pond(pond_id) -> None:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE ponds
                SET desired_state = 'stopped', host_port = 1
                WHERE id = :id
                """
            ),
            {"id": pond_id},
        )
        connection.execute(
            text(
                """
                UPDATE pond_status
                SET observed_state = 'stopped', healthy = false
                WHERE pond_id = :id
                """
            ),
            {"id": pond_id},
        )
    engine.dispose()


def test_user_sql_error_is_4xx() -> None:
    pond = seed_probe_pond()
    headers = _headers()
    queries = (
        "SELECT * FROM table_that_is_not_there",
        "SELEC 1",
    )
    for query in queries:
        response = client.post(
            f"/api/v1/ponds/{pond.pond_id}/sql",
            headers=headers,
            json={"query": query, "mode": "read"},
        )
        assert 400 <= response.status_code < 500, response.text
        body = response.json()
        assert body["code"] == "sql_error"
        assert body["message"] == (
            "No se pudo ejecutar la consulta. Revisa la sintaxis, la tabla o los permisos."
        )
        leaked = response.text.lower()
        assert "asyncpg" not in leaked
        assert "traceback" not in leaked
        assert "does not exist" not in leaked
        assert "syntax error" not in leaked


def test_sql_endpoint_caps_rows_at_1000() -> None:
    pond = seed_probe_pond()
    response = client.post(
        f"/api/v1/ponds/{pond.pond_id}/sql",
        headers=_headers(),
        json={"query": "SELECT generate_series(1, 1001)", "mode": "read"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["row_count"] == 1000
    assert body["truncated"] is True
    assert len(body["rows"]) == 1000


def test_sql_endpoint_timeout_returns_sql_timeout() -> None:
    pond = seed_probe_pond()
    response = client.post(
        f"/api/v1/ponds/{pond.pond_id}/sql",
        headers=_headers(),
        json={"query": "SELECT pg_sleep(30)", "mode": "read"},
    )

    assert response.status_code == 504, response.text
    assert response.json()["code"] == "sql_timeout"
    assert "asyncpg" not in response.text.lower()


def _pond_admin_url() -> str:
    base = to_sync_database_url(get_settings().database_url).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return base.rsplit("/", 1)[0] + f"/{PROBE_DATABASE}"


def _sql(pond_id, headers: dict[str, str], query: str, mode: str):
    return client.post(
        f"/api/v1/ponds/{pond_id}/sql",
        headers=headers,
        json={"query": query, "mode": mode},
    )


def _remove_server_file(path: str) -> None:
    statement = sql.SQL("COPY (SELECT 1) TO PROGRAM {}").format(sql.Literal(f"rm -f {path}"))
    with psycopg.connect(_pond_admin_url(), autocommit=True) as conn:
        conn.execute(statement)


def _server_file_present(path: str) -> bool:
    with psycopg.connect(_pond_admin_url(), autocommit=True) as conn:
        row = conn.execute(
            "SELECT (pg_stat_file(%s, true)).size IS NOT NULL",
            (path,),
        ).fetchone()
    return bool(row and row[0])


def _install_superuser_console_role() -> None:
    with psycopg.connect(_pond_admin_url(), autocommit=True) as conn:
        conn.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'koi_console') THEN
                CREATE ROLE koi_console LOGIN SUPERUSER;
              ELSE
                ALTER ROLE koi_console WITH LOGIN SUPERUSER;
              END IF;
            END $$
            """
        )
        conn.execute(
            """
            GRANT pg_read_server_files, pg_write_server_files, pg_execute_server_program
            TO koi_console
            """
        )


def _install_superuser_owned_app_table() -> None:
    with psycopg.connect(_pond_admin_url(), autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS app CASCADE")
        conn.execute("CREATE SCHEMA app AUTHORIZATION postgres")
        conn.execute("CREATE TABLE app.legacy (n integer)")
        conn.execute("INSERT INTO app.legacy (n) VALUES (3)")
        conn.execute("ALTER TABLE app.legacy OWNER TO postgres")


def test_copy_program_returns_sql_error_and_runs_nothing() -> None:
    pond = seed_probe_pond()
    _remove_server_file(COPY_MARKER)
    response = _sql(pond.pond_id, _headers(), COPY_PROGRAM, "write")

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["code"] == "sql_error"
    assert body["message"] == SQL_ERROR_MESSAGE
    assert "asyncpg" not in response.text.lower()
    assert "program" not in response.text.lower()
    assert _server_file_present(COPY_MARKER) is False


def test_console_session_is_not_superuser_and_not_a_server_file_role() -> None:
    pond = seed_probe_pond()
    _install_superuser_console_role()
    headers = _headers()

    superuser = _sql(pond.pond_id, headers, ROL_SUPER, "read")
    assert superuser.status_code == 200, superuser.text
    assert superuser.json()["rows"] == [[False]]

    member = _sql(pond.pond_id, headers, SERVER_FILE_MEMBER, "read")
    assert member.status_code == 200, member.text
    assert member.json()["rows"] == [[False]]

    who = _sql(pond.pond_id, headers, "SELECT current_user", "read")
    assert who.status_code == 200, who.text
    assert who.json()["rows"] == [[CONSOLE_ROLE]]

    owns = _sql(pond.pond_id, headers, OWNS_APP, "read")
    assert owns.status_code == 200, owns.text
    assert owns.json()["rows"] == [[True]]


def test_console_reads_and_writes_app_data_and_can_create_a_table() -> None:
    pond = seed_probe_pond()
    _install_superuser_owned_app_table()
    headers = _headers()

    legacy = _sql(pond.pond_id, headers, "SELECT n FROM app.legacy", "read")
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["rows"] == [[3]]

    added = _sql(pond.pond_id, headers, "INSERT INTO app.legacy (n) VALUES (9)", "write")
    assert added.status_code == 200, added.text
    again = _sql(pond.pond_id, headers, "SELECT n FROM app.legacy ORDER BY n", "read")
    assert again.status_code == 200, again.text
    assert again.json()["rows"] == [[3], [9]]

    created = _sql(
        pond.pond_id,
        headers,
        "CREATE TABLE console_note (n integer)",
        "write",
    )
    assert created.status_code == 200, created.text
    inserted = _sql(
        pond.pond_id,
        headers,
        "INSERT INTO console_note (n) VALUES (7)",
        "write",
    )
    assert inserted.status_code == 200, inserted.text
    selected = _sql(pond.pond_id, headers, "SELECT n FROM console_note", "read")
    assert selected.status_code == 200, selected.text
    assert selected.json()["rows"] == [[7]]

    probe = _sql(pond.pond_id, headers, PROBE_QUERY, "read")
    assert probe.status_code == 200, probe.text
    assert probe.json()["rows"] == [[PROBE_VALUE]]
    written = _sql(pond.pond_id, headers, WRITE_INSERT, "write")
    assert written.status_code == 200, written.text
    assert probe_values() == [7, PROBE_VALUE]


def test_sql_endpoint_stopped_pond_returns_node_unavailable() -> None:
    pond = seed_probe_pond()
    _close_stopped_pond(pond.pond_id)
    response = client.post(
        f"/api/v1/ponds/{pond.pond_id}/sql",
        headers=_headers(),
        json={"query": PROBE_QUERY, "mode": "read"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "node_unavailable"
