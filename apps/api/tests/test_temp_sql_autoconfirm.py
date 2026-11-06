"""Phase 1 tests for issue #205 — temp-access SQL auto-confirm.

One named test per statechart path from
docs/architecture/statecharts/temp-sql-autoconfirm/README.md.
No production code in the test: commit: these must fail until Phase 2.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.commands import sql as sql_commands
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.enums import AppSurface, SQLMode, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.main import app
from app.schemas import ConfirmationRequiredResponse, RunSQLRequest, SQLResultResponse
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user
from tests.sql_probe_pond import probe_values, seed_probe_pond

client = TestClient(app)

SAFE_CREATE = "CREATE TABLE IF NOT EXISTS demo_temp (id integer PRIMARY KEY)"
SAFE_INSERT = "INSERT INTO demo_temp (id) VALUES (1) ON CONFLICT DO NOTHING"
LONG_SLEEP = "SELECT pg_sleep(30)"


def _auth_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _basic(slug: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _create_temp_access(headers: dict[str, str], pond_id: str) -> dict:
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    response = client.post(
        f"/api/v1/ponds/{pond_id}/temp-access",
        headers=headers,
        json={"expires_at": expires_at, "scopes": ["whoami", "get_pond", "run_sql"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _temp_actor(user_id, pond_id: str) -> AuthContext:
    return AuthContext(
        user_id=str(user_id),
        email=DEMO_EMAIL,
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.MCP,
        pond_id=str(pond_id),
        allowed_tools=frozenset({"whoami", "get_pond", "run_sql"}),
    )


def _account_actor(user_id) -> AuthContext:
    return AuthContext(
        user_id=str(user_id),
        email=DEMO_EMAIL,
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.MCP,
    )


def _mcp_run_sql(mcp: dict[str, str], pond_name: str, query: str, mode: str = "write") -> dict:
    response = client.post(
        "/mcp",
        headers=mcp,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "run_sql",
            "params": {"pond_name": pond_name, "query": query, "mode": mode},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "error" not in body or body.get("result") is not None, body
    return body.get("result") or {}


# --- Path 1: temp auto-confirm ---


async def test_temp_actor_safe_create_table_auto_confirms_without_confirm_action() -> None:
    """Idle (temp) → Running (temp auto-confirm) → Success for CREATE TABLE."""
    pond = seed_probe_pond()
    result = await sql_commands.run_sql(
        pond.pond_id,
        RunSQLRequest(query=SAFE_CREATE, mode=SQLMode.WRITE),
        actor=_temp_actor(pond.user_id, pond.pond_id),
        surface=AppSurface.MCP,
    )
    assert not isinstance(result, ConfirmationRequiredResponse)
    assert isinstance(result, SQLResultResponse)


async def test_temp_actor_safe_insert_auto_confirms_without_confirm_action() -> None:
    """Idle (temp) → Running (temp auto-confirm) → Success for INSERT."""
    pond = seed_probe_pond()
    await sql_commands.run_sql(
        pond.pond_id,
        RunSQLRequest(query=SAFE_CREATE, mode=SQLMode.WRITE),
        actor=_temp_actor(pond.user_id, pond.pond_id),
        surface=AppSurface.MCP,
    )
    result = await sql_commands.run_sql(
        pond.pond_id,
        RunSQLRequest(query=SAFE_INSERT, mode=SQLMode.WRITE),
        actor=_temp_actor(pond.user_id, pond.pond_id),
        surface=AppSurface.MCP,
    )
    assert not isinstance(result, ConfirmationRequiredResponse)
    assert isinstance(result, SQLResultResponse)


# --- Path 2: account confirm unchanged ---


async def test_account_actor_write_still_requires_confirmation() -> None:
    """Idle (account) → Confirm write. First write stays confirmation_required."""
    pond = seed_probe_pond()
    result = await sql_commands.run_sql(
        pond.pond_id,
        RunSQLRequest(query=SAFE_INSERT, mode=SQLMode.WRITE),
        actor=_account_actor(pond.user_id),
        surface=AppSurface.MCP,
    )
    assert isinstance(result, ConfirmationRequiredResponse)
    assert result.status == "confirmation_required"
    assert result.token


# --- Path 3: dangerous blocked ---


@pytest.mark.parametrize(
    "query",
    [
        "DROP DATABASE postgres",
        "DROP ROLE postgres",
        "ALTER SYSTEM SET listen_addresses = '*'",
        "COPY probe TO PROGRAM 'id'",
    ],
)
async def test_temp_actor_dangerous_statement_is_rejected_without_execution(query: str) -> None:
    """Idle (temp) → Blocked (dangerous SQL). No execution."""
    pond = seed_probe_pond()
    before = probe_values()
    with pytest.raises(AppError) as raised:
        result = await sql_commands.run_sql(
            pond.pond_id,
            RunSQLRequest(query=query, mode=SQLMode.WRITE),
            actor=_temp_actor(pond.user_id, pond.pond_id),
            surface=AppSurface.MCP,
        )
        assert not isinstance(result, ConfirmationRequiredResponse), (
            "dangerous SQL must be rejected, not deferred to confirm_action"
        )
    assert raised.value.code == ErrorCode.SQL_ERROR
    assert probe_values() == before


# --- Path 4: privilege blocked ---


@pytest.mark.parametrize(
    "query",
    [
        "GRANT ALL ON TABLE probe TO PUBLIC",
        "REVOKE ALL ON TABLE probe FROM PUBLIC",
        "ALTER ROLE postgres WITH SUPERUSER",
    ],
)
async def test_temp_actor_privilege_change_is_rejected_without_execution(query: str) -> None:
    """Idle (temp) → Blocked (privilege change). No execution."""
    pond = seed_probe_pond()
    before = probe_values()
    with pytest.raises(AppError) as raised:
        result = await sql_commands.run_sql(
            pond.pond_id,
            RunSQLRequest(query=query, mode=SQLMode.WRITE),
            actor=_temp_actor(pond.user_id, pond.pond_id),
            surface=AppSurface.MCP,
        )
        assert not isinstance(result, ConfirmationRequiredResponse), (
            "privilege SQL must be rejected, not deferred to confirm_action"
        )
    assert raised.value.code == ErrorCode.SQL_ERROR
    assert probe_values() == before


# --- Path 5: timeout ---


async def test_temp_actor_long_running_sql_aborted_by_statement_timeout() -> None:
    """Idle (temp) → Running (long query) → Timed out. Not confirmation_required."""
    pond = seed_probe_pond()
    with pytest.raises(AppError) as raised:
        result = await sql_commands.run_sql(
            pond.pond_id,
            RunSQLRequest(query=LONG_SLEEP, mode=SQLMode.WRITE),
            actor=_temp_actor(pond.user_id, pond.pond_id),
            surface=AppSurface.MCP,
        )
        assert not isinstance(result, ConfirmationRequiredResponse), (
            "long-running write under temp access must run (and time out), not confirm"
        )
    assert raised.value.code == ErrorCode.SQL_TIMEOUT


# --- Path 6: rate limit ---


async def test_temp_actor_exceeding_rate_limit_returns_rate_limited() -> None:
    """Idle (temp) → Rate limited once the per-token window is exceeded."""
    pond = seed_probe_pond()
    actor = _temp_actor(pond.user_id, pond.pond_id)
    # Burn the window with cheap reads that still count against the token.
    last_error: AppError | None = None
    for _ in range(30):
        try:
            await sql_commands.run_sql(
                pond.pond_id,
                RunSQLRequest(query="SELECT 1", mode=SQLMode.READ),
                actor=actor,
                surface=AppSurface.MCP,
            )
        except AppError as exc:
            last_error = exc
            break
    assert last_error is not None
    assert last_error.code == ErrorCode.RATE_LIMITED

    with pytest.raises(AppError) as raised:
        await sql_commands.run_sql(
            pond.pond_id,
            RunSQLRequest(query="SELECT 1", mode=SQLMode.READ),
            actor=actor,
            surface=AppSurface.MCP,
        )
    assert raised.value.code == ErrorCode.RATE_LIMITED


# --- MCP surface smoke for the demo path ---


def test_mcp_temp_access_safe_write_skips_confirm_round_trip() -> None:
    """Demo surface: MCP temp slug runs CREATE TABLE without confirm_action."""
    pond = seed_probe_pond()
    # seed_probe_pond resets users; mint the bearer after the pond exists.
    headers = _auth_headers()
    created = _create_temp_access(headers, str(pond.pond_id))
    mcp = _basic(created["slug"], created["password"])
    result = _mcp_run_sql(mcp, "sql-probe", SAFE_CREATE, mode="write")
    assert result.get("status") != "confirmation_required", result
    assert result.get("code") not in {"confirmation_required"}, result
    assert "columns" in result or result.get("status") != "error", result
