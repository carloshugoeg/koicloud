"""SQL console against a real pond database, not the OpenAPI example."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.commands.sql import run_sql
from app.core.auth import AuthContext
from app.core.config import get_settings, to_sync_database_url
from app.core.enums import AppSurface, SQLMode, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.main import app
from app.schemas import RunSQLRequest, SQLResultResponse
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD
from tests.sql_probe_pond import PROBE_QUERY, PROBE_VALUE, probe_values, seed_probe_pond

WRITE_INSERT = "INSERT INTO probe (n) VALUES (7)"

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
