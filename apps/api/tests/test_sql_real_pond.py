"""SQL console against a real pond database, not the OpenAPI example."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.commands.sql import run_sql
from app.core.auth import AuthContext
from app.core.enums import AppSurface, SQLMode, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.main import app
from app.schemas import RunSQLRequest, SQLResultResponse
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD
from tests.sql_probe_pond import PROBE_QUERY, PROBE_VALUE, probe_values, seed_probe_pond

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
