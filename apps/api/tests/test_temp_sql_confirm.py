"""Red-first wire matrix for bound temporary MCP SQL confirmation (TEMP-CONFIRM §6).

Organizing structure: proposal state machine NoProposal → Pending → Consumed,
with independent credential Live / Expired / Revoked. Logical session = PondToken.id.
Asserts observable wire behavior only (status, code, table presence), not internals.
"""

from __future__ import annotations

import base64
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.commands import sql as sql_commands
from app.core.auth import AuthContext
from app.core.config import get_settings, to_sync_database_url
from app.core.enums import AppSurface, SQLMode, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.security import hash_password
from app.main import app
from app.schemas import RunSQLRequest
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables
from tests.sql_probe_pond import (
    PROBE_DATABASE,
    seed_probe_pond,
)

TRANSPORTS = ("jsonrpc", "streamable")
STREAM_ACCEPT = "application/json, text/event-stream"
COPY_MARKER = "/tmp/koicloud-temp-confirm-copy-marker"
COPY_PROGRAM = f"COPY (SELECT 1) TO PROGRAM 'touch {COPY_MARKER}'"

client = TestClient(app)

# Streamable HTTP needs the FastMCP lifespan task group. One shared TestClient
# with an entered lifespan keeps concurrent confirms from racing nested lifespans.
_STREAM_LOCK = threading.Lock()
_STREAM_CM: TestClient | None = None
_STREAM_CLIENT: TestClient | None = None


def _stream_client() -> TestClient:
    global _STREAM_CM, _STREAM_CLIENT
    with _STREAM_LOCK:
        if _STREAM_CLIENT is None:
            _STREAM_CM = TestClient(app)
            _STREAM_CLIENT = _STREAM_CM.__enter__()
        return _STREAM_CLIENT


@dataclass(frozen=True, slots=True)
class TempAudience:
    pond_id: str
    pond_name: str
    token_id: str
    slug: str
    password: str
    basic: dict[str, str]
    owner: dict[str, str]


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _basic(slug: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _owner_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _account_mcp_headers() -> dict[str, str]:
    settings = get_settings()
    return _basic(settings.mcp_demo_slug, settings.mcp_demo_password)


def _engine():
    return create_engine(to_sync_database_url(get_settings().database_url))


def _probe_admin_url() -> str:
    base = to_sync_database_url(get_settings().database_url).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return base.rsplit("/", 1)[0] + f"/{PROBE_DATABASE}"


def _table_exists(qualified: str) -> bool:
    schema, _, name = qualified.partition(".")
    if not name:
        schema, name = "public", schema
    with psycopg.connect(_probe_admin_url(), autocommit=True) as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema, name),
        ).fetchone()
    return row is not None


def _drop_table_if_exists(qualified: str) -> None:
    with psycopg.connect(_probe_admin_url(), autocommit=True) as conn:
        conn.execute(f"DROP TABLE IF EXISTS {qualified}")


def _create_temp_access(
    owner: dict[str, str],
    pond_id: str,
    *,
    expires_in_seconds: int = 3600,
    scopes: list[str] | None = None,
) -> dict:
    expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in_seconds)).isoformat()
    payload: dict = {"expires_at": expires_at}
    if scopes is not None:
        payload["scopes"] = scopes
    else:
        payload["scopes"] = ["whoami", "get_pond", "run_sql"]
    response = client.post(
        f"/api/v1/ponds/{pond_id}/temp-access",
        headers=owner,
        json=payload,
    )
    body = response.json() if response.content else {}
    return {"response": response, "body": body}


def _seed_audience(
    *,
    expires_in_seconds: int = 3600,
    scopes: list[str] | None = None,
) -> TempAudience:
    pond = seed_probe_pond()
    owner = _owner_headers()
    created = _create_temp_access(
        owner,
        str(pond.pond_id),
        expires_in_seconds=expires_in_seconds,
        scopes=scopes,
    )
    assert created["response"].status_code == 201, created["response"].text
    body = created["body"]
    return TempAudience(
        pond_id=str(pond.pond_id),
        pond_name="sql-probe",
        token_id=body["id"],
        slug=body["slug"],
        password=body["password"],
        basic=_basic(body["slug"], body["password"]),
        owner=owner,
    )


def _parse_sse_messages(raw: str) -> list[dict]:
    messages: list[dict] = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                messages.append(json.loads(line[5:].strip()))
    return messages


def _mcp_call(
    transport: str,
    headers: dict[str, str],
    tool: str,
    arguments: dict,
    *,
    rpc_id: int | str = 1,
) -> tuple[int, dict]:
    """Call an MCP tool over JSON-RPC or Streamable HTTP. Returns (http_status, result_dict)."""
    if transport == "jsonrpc":
        response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": rpc_id,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            },
        )
        if response.status_code != 200:
            return response.status_code, response.json()
        body = response.json()
        result = body.get("result")
        assert isinstance(result, dict), body
        return response.status_code, result

    if transport != "streamable":
        raise AssertionError(f"unknown transport {transport}")

    response = _stream_client().post(
        "/mcp",
        headers={
            **headers,
            "Accept": STREAM_ACCEPT,
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
    )
    if response.status_code != 200:
        try:
            return response.status_code, response.json()
        except Exception:
            return response.status_code, {"raw": response.text}
    assert "text/event-stream" in response.headers.get("content-type", ""), response.headers
    messages = _parse_sse_messages(response.text)
    assert messages, response.text
    envelope = messages[-1]
    result = envelope.get("result") or {}
    if result.get("structuredContent"):
        data = result["structuredContent"]
        assert isinstance(data, dict), data
        return response.status_code, data
    if result.get("isError"):
        text_bits = [
            part.get("text", "")
            for part in result.get("content") or []
            if isinstance(part, dict)
        ]
        joined = " ".join(text_bits)
        code = None
        for candidate in (
            "confirmation_not_found",
            "confirmation_expired",
            "confirmation_action_mismatch",
            "agent_bad_credentials",
            "agent_disabled",
            "sql_readonly_violation",
            "sql_error",
            "pond_not_found",
        ):
            if candidate in joined:
                code = candidate
                break
        if code is None:
            # Streamable FastMCP surfaces AppError.message (Spanish catalog text)
            # without the machine code; map the known TEMP-CONFIRM messages.
            from app.core.errors import ERROR_CATALOG, ErrorCode

            for candidate in (
                ErrorCode.CONFIRMATION_NOT_FOUND,
                ErrorCode.CONFIRMATION_EXPIRED,
                ErrorCode.CONFIRMATION_ACTION_MISMATCH,
                ErrorCode.AGENT_BAD_CREDENTIALS,
                ErrorCode.AGENT_DISABLED,
                ErrorCode.SQL_READONLY_VIOLATION,
                ErrorCode.SQL_ERROR,
                ErrorCode.POND_NOT_FOUND,
            ):
                if ERROR_CATALOG[candidate].message in joined:
                    code = candidate.value
                    break
        return response.status_code, {
            "status": "error",
            "code": code,
            "message": joined,
            "isError": True,
        }
    # Fallback: parse text JSON content when structuredContent is absent.
    for part in result.get("content") or []:
        if isinstance(part, dict) and part.get("type") == "text":
            try:
                parsed = json.loads(part["text"])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(parsed, dict):
                return response.status_code, parsed
    return response.status_code, result if isinstance(result, dict) else {"result": result}


def _create_sql(table: str) -> str:
    return f"CREATE TABLE {table} (id integer)"


def _propose_write(
    transport: str,
    audience: TempAudience,
    query: str,
    *,
    mode: str = "write",
    pond_name: str | None = None,
) -> tuple[int, dict]:
    return _mcp_call(
        transport,
        audience.basic,
        "run_sql",
        {
            "pond_name": pond_name or audience.pond_name,
            "query": query,
            "mode": mode,
        },
    )


def _confirm(
    transport: str,
    headers: dict[str, str],
    token: str,
    *,
    extra_args: dict | None = None,
) -> tuple[int, dict]:
    arguments = {"token": token}
    if extra_args:
        arguments.update(extra_args)
    return _mcp_call(transport, headers, "confirm_action", arguments)


def _pending_count(*, token_prefix: str | None = None) -> int:
    engine = _engine()
    with engine.begin() as connection:
        if token_prefix:
            count = connection.execute(
                text(
                    """
                    SELECT count(*) FROM pending_confirmations
                    WHERE summary LIKE :needle OR action = 'run_sql_write'
                    """
                ),
                {"needle": f"%{token_prefix}%"},
            ).scalar_one()
        else:
            count = connection.execute(
                text("SELECT count(*) FROM pending_confirmations")
            ).scalar_one()
    engine.dispose()
    return int(count)


def _sql_history_count(pond_id: str, query: str) -> int:
    engine = _engine()
    with engine.begin() as connection:
        count = connection.execute(
            text(
                """
                SELECT count(*) FROM sql_history
                WHERE pond_id = :pond_id AND query_truncated = :query
                """
            ),
            {"pond_id": pond_id, "query": query},
        ).scalar_one()
    engine.dispose()
    return int(count)


def _expire_pond_token(token_id: str) -> None:
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE pond_tokens
                SET expires_at = CURRENT_TIMESTAMP - interval '1 minute'
                WHERE id = :id
                """
            ),
            {"id": token_id},
        )
    engine.dispose()


def _revoke_pond_token(audience: TempAudience) -> None:
    response = client.post(
        f"/api/v1/ponds/{audience.pond_id}/temp-access/{audience.token_id}/revoke",
        headers=audience.owner,
    )
    assert response.status_code == 200, response.text


def _expire_proposal(token: str) -> None:
    from app.core.security import hash_token

    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE pending_confirmations
                SET expires_at = CURRENT_TIMESTAMP - interval '1 minute'
                WHERE token_hash = :hash
                """
            ),
            {"hash": hash_token(token)},
        )
    engine.dispose()


def _insert_second_owned_pond(owner_pond_id: str, name: str) -> str:
    pond_b_id = str(uuid.uuid4())
    engine = _engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT user_id, plan_id, node_id, host_port, db_password_encrypted, engine_version
                FROM ponds WHERE id = :id
                """
            ),
            {"id": owner_pond_id},
        ).one()
        connection.execute(
            text(
                """
                INSERT INTO ponds (
                    id, user_id, plan_id, node_id, name, engine_version,
                    desired_state, host_port, db_password_encrypted, created_at
                ) VALUES (
                    :id, :user_id, :plan_id, :node_id, :name, :engine_version,
                    'running', :host_port, :db_password_encrypted, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": pond_b_id,
                "user_id": row.user_id,
                "plan_id": row.plan_id,
                "node_id": row.node_id,
                "name": name,
                "engine_version": row.engine_version,
                "host_port": int(row.host_port) + 1,
                "db_password_encrypted": row.db_password_encrypted,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO pond_status (pond_id, observed_state, healthy)
                VALUES (:id, 'running', true)
                """
            ),
            {"id": pond_b_id},
        )
    engine.dispose()
    return pond_b_id


def _other_user_audience(pond_id_for_port_base: str) -> TempAudience:
    """Create a second owner with their own pond + temp credential (same probe DB)."""
    other_email = f"other-{uuid.uuid4().hex[:8]}@koicloud.dev"
    other_password = "OtherSegura!2026"
    other_user_id = str(uuid.uuid4())
    other_pond_id = str(uuid.uuid4())
    other_pond_name = _unique("otherpond")
    engine = _engine()
    with engine.begin() as connection:
        base = connection.execute(
            text(
                """
                SELECT plan_id, node_id, host_port, db_password_encrypted, engine_version
                FROM ponds WHERE id = :id
                """
            ),
            {"id": pond_id_for_port_base},
        ).one()
        connection.execute(
            text(
                """
                INSERT INTO users (
                    id, email, password_hash, full_name, role, status, email_verified_at
                ) VALUES (
                    :id, :email, :password_hash, 'Other', 'client', 'active', CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": other_user_id,
                "email": other_email,
                "password_hash": hash_password(other_password),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO ponds (
                    id, user_id, plan_id, node_id, name, engine_version,
                    desired_state, host_port, db_password_encrypted, created_at
                ) VALUES (
                    :id, :user_id, :plan_id, :node_id, :name, :engine_version,
                    'running', :host_port, :db_password_encrypted, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": other_pond_id,
                "user_id": other_user_id,
                "plan_id": base.plan_id,
                "node_id": base.node_id,
                "name": other_pond_name,
                "engine_version": base.engine_version,
                "host_port": int(base.host_port) + 7,
                "db_password_encrypted": base.db_password_encrypted,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO pond_status (pond_id, observed_state, healthy)
                VALUES (:id, 'running', true)
                """
            ),
            {"id": other_pond_id},
        )
    engine.dispose()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": other_email, "password": other_password},
    )
    assert login.status_code == 200, login.text
    owner = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = _create_temp_access(owner, other_pond_id)
    assert created["response"].status_code == 201, created["response"].text
    body = created["body"]
    return TempAudience(
        pond_id=other_pond_id,
        pond_name=other_pond_name,
        token_id=body["id"],
        slug=body["slug"],
        password=body["password"],
        basic=_basic(body["slug"], body["password"]),
        owner=owner,
    )


def _assert_tool_error(result: dict, code: str) -> None:
    assert result.get("status") == "error", result
    assert result.get("code") == code, result


def _assert_gate_failure(status_code: int, body: dict, code: str) -> None:
    assert status_code in {401, 403}, (status_code, body)
    assert body.get("code") == code, body


# --- NoProposal → Pending / Consumed happy path ---


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_create_table_propose_without_owner_jwt(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    query = _create_sql(table)

    status, result = _propose_write(transport, audience, query)

    assert status == 200, result
    assert result.get("status") == "confirmation_required", result
    assert result.get("token"), result
    assert isinstance(result.get("summary"), str) and result["summary"]
    assert result.get("expires_at")
    nxt = result.get("next") or {}
    assert nxt.get("confirm_url") == "/mcp", nxt
    assert nxt.get("cli_example") == "", nxt
    assert _table_exists(table) is False
    # No owner JWT on this call: only Basic was sent.
    assert "Bearer" not in audience.basic.get("Authorization", "")


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_create_table_confirm_without_owner_jwt(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    query = _create_sql(table)

    status, proposed = _propose_write(transport, audience, query)
    assert status == 200, proposed
    assert proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    status, confirmed = _confirm(transport, audience.basic, token)
    assert status == 200, confirmed
    assert confirmed.get("status") != "error", confirmed
    assert "columns" in confirmed, confirmed
    assert "rows" in confirmed, confirmed
    assert isinstance(confirmed.get("row_count"), int), confirmed
    assert _table_exists(table) is True

    status, read = _propose_write(
        transport,
        audience,
        f"SELECT 1 FROM {table}",
        mode="read",
    )
    assert status == 200, read
    assert read.get("status") != "error", read
    assert read.get("row_count") == 0, read


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_read_sql_unchanged(transport: str) -> None:
    audience = _seed_audience()
    before = _pending_count()
    status, result = _propose_write(
        transport,
        audience,
        "SELECT 1 AS n",
        mode="read",
    )
    assert status == 200, result
    assert result.get("status") != "confirmation_required", result
    assert result.get("columns") == ["n"], result
    assert result.get("rows") == [[1]], result
    assert _pending_count() == before


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_write_in_read_mode_still_denied(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    status, result = _propose_write(
        transport,
        audience,
        _create_sql(table),
        mode="read",
    )
    assert status == 200, result
    _assert_tool_error(result, "sql_readonly_violation")
    assert _table_exists(table) is False


# --- Session / pond / binding denials ---


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_other_session_same_pond_cannot_confirm(transport: str) -> None:
    audience = _seed_audience()
    other = _create_temp_access(audience.owner, audience.pond_id)
    assert other["response"].status_code == 201, other["response"].text
    other_basic = _basic(other["body"]["slug"], other["body"]["password"])

    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed

    status, denied = _confirm(transport, other_basic, proposed["token"])
    assert status == 200, denied
    _assert_tool_error(denied, "confirmation_not_found")
    assert _table_exists(table) is False


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_cross_pond_and_user_cannot_confirm(transport: str) -> None:
    audience = _seed_audience()
    foreign = _other_user_audience(audience.pond_id)

    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed

    status, denied = _confirm(transport, foreign.basic, proposed["token"])
    assert status == 200, denied
    _assert_tool_error(denied, "confirmation_not_found")
    assert _table_exists(table) is False


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_other_pond_proposal_denied(transport: str) -> None:
    audience = _seed_audience()
    other_name = _unique("beta")
    _insert_second_owned_pond(audience.pond_id, other_name)

    status, result = _propose_write(
        transport,
        audience,
        "SELECT 1",
        mode="read",
        pond_name=other_name,
    )
    assert status == 200, result
    _assert_tool_error(result, "pond_not_found")


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_tampered_binding_never_executes(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    evil = f"app.{_unique('evil')}"
    _drop_table_if_exists(table)
    _drop_table_if_exists(evil)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    from app.core.security import hash_token

    engine = _engine()
    with engine.begin() as connection:
        # Tamper stored SQL / binding. Columns may be absent until migration (still red).
        connection.execute(
            text(
                """
                UPDATE pending_confirmations
                SET payload = jsonb_set(
                    payload,
                    '{request,query}',
                    to_jsonb(CAST(:evil AS text)),
                    true
                )
                WHERE token_hash = :hash
                """
            ),
            {"evil": _create_sql(evil), "hash": hash_token(token)},
        )
        cols = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'pending_confirmations'
                      AND column_name IN ('request_digest', 'pond_token_id', 'pond_id')
                    """
                )
            )
        }
        assert cols == {"request_digest", "pond_token_id", "pond_id"}
        connection.execute(
            text(
                """
                UPDATE pending_confirmations
                SET request_digest = :digest
                WHERE token_hash = :hash
                """
            ),
            {"digest": "0" * 64, "hash": hash_token(token)},
        )
    engine.dispose()

    status, denied = _confirm(transport, audience.basic, token)
    assert status == 200, denied
    assert denied.get("code") in {
        "confirmation_action_mismatch",
        "confirmation_not_found",
    }, denied
    assert _table_exists(table) is False
    assert _table_exists(evil) is False


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_confirm_arguments_cannot_override_proposal(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    override = f"app.{_unique('ovr')}"
    _drop_table_if_exists(table)
    _drop_table_if_exists(override)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed

    status, confirmed = _confirm(
        transport,
        audience.basic,
        proposed["token"],
        extra_args={
            "query": _create_sql(override),
            "mode": "write",
            "pond_id": str(uuid.uuid4()),
            "action": "delete_pond",
            "pond_token_id": str(uuid.uuid4()),
        },
    )
    assert status == 200, confirmed
    # Either confirm succeeds with the *original* binding, or extras are rejected.
    # The override table must never appear; original may appear only on success.
    assert _table_exists(override) is False
    if confirmed.get("status") != "error":
        assert _table_exists(table) is True
    else:
        assert confirmed.get("code") in {
            "confirmation_not_found",
            "confirmation_action_mismatch",
            "agent_disabled",
        }, confirmed
        assert _table_exists(table) is False


# --- Consume / replay / concurrency ---


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_confirmation_replay_denied(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    query = _create_sql(table)

    status, proposed = _propose_write(transport, audience, query)
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    status, first = _confirm(transport, audience.basic, token)
    assert status == 200 and first.get("status") != "error", first
    assert _table_exists(table) is True
    history_after_first = _sql_history_count(audience.pond_id, query)

    status, replay = _confirm(transport, audience.basic, token)
    assert status == 200, replay
    _assert_tool_error(replay, "confirmation_not_found")
    assert _sql_history_count(audience.pond_id, query) == history_after_first


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_confirmation_concurrent_single_consume(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    query = _create_sql(table)

    status, proposed = _propose_write(transport, audience, query)
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]
    barrier = threading.Barrier(2)

    def worker() -> tuple[int, dict]:
        barrier.wait()
        return _confirm(transport, audience.basic, token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: worker(), range(2)))

    successes = [
        result
        for status, result in outcomes
        if status == 200 and result.get("status") != "error" and "columns" in result
    ]
    denials = [
        result
        for status, result in outcomes
        if status == 200 and result.get("code") == "confirmation_not_found"
    ]
    assert len(successes) == 1, outcomes
    assert len(denials) == 1, outcomes
    assert _table_exists(table) is True
    assert _sql_history_count(audience.pond_id, query) == 1


# --- Credential / proposal expiry and revoke ---


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_expired_or_revoked_before_issue_denied(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    before = _pending_count()

    _revoke_pond_token(audience)
    status, revoked = _propose_write(transport, audience, _create_sql(table))
    _assert_gate_failure(status, revoked, "agent_bad_credentials")
    assert _pending_count() == before
    assert _table_exists(table) is False

    audience = _seed_audience()
    _expire_pond_token(audience.token_id)
    before = _pending_count()
    status, expired = _propose_write(transport, audience, _create_sql(table))
    _assert_gate_failure(status, expired, "agent_bad_credentials")
    assert _pending_count() == before


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_expired_or_revoked_before_confirm_denied(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    _revoke_pond_token(audience)
    status, denied = _confirm(transport, audience.basic, token)
    if status in {401, 403}:
        _assert_gate_failure(status, denied, "agent_bad_credentials")
    else:
        assert status == 200, denied
        assert denied.get("code") == "agent_bad_credentials", denied
    assert _table_exists(table) is False

    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    _expire_pond_token(audience.token_id)
    status, denied = _confirm(transport, audience.basic, proposed["token"])
    if status in {401, 403}:
        _assert_gate_failure(status, denied, "agent_bad_credentials")
    else:
        assert status == 200, denied
        assert denied.get("code") == "agent_bad_credentials", denied
    assert _table_exists(table) is False


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_proposal_expired_while_session_live(transport: str) -> None:
    audience = _seed_audience(expires_in_seconds=3600)
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]
    _expire_proposal(token)

    status, denied = _confirm(transport, audience.basic, token)
    assert status == 200, denied
    _assert_tool_error(denied, "confirmation_expired")
    assert _table_exists(table) is False
    # Credential still authenticates for read.
    status, read = _propose_write(transport, audience, "SELECT 1 AS n", mode="read")
    assert status == 200, read
    assert read.get("rows") == [[1]], read


def test_temp_revoked_or_expired_between_claim_and_submit() -> None:
    """Revoke after durable claim but before SQL admission: 401, no table, token spent.

    Uses a FOR UPDATE barrier on pond_tokens so the confirm path (once it locks
    that row) can observe revoke-before-admission. No production hook invented.
    """
    transport = "jsonrpc"
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    ready = threading.Barrier(2)
    hold_done = threading.Event()
    outcomes: list[tuple[int, dict]] = []

    def holder() -> None:
        engine = _engine()
        with engine.connect() as connection:
            connection.execute(
                text("SELECT id FROM pond_tokens WHERE id = :id FOR UPDATE"),
                {"id": audience.token_id},
            )
            ready.wait()
            connection.execute(
                text(
                    """
                    UPDATE pond_tokens
                    SET revoked_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": audience.token_id},
            )
            connection.commit()
            hold_done.set()
        engine.dispose()

    def confirmer() -> None:
        ready.wait()
        # Confirm starts while holder may still hold / just revoked under the same lock order.
        outcomes.append(_confirm(transport, audience.basic, token))
        hold_done.wait(timeout=10)

    threads = [threading.Thread(target=holder), threading.Thread(target=confirmer)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert outcomes, "confirm never ran"
    status, result = outcomes[0]
    if status in {401, 403}:
        assert result.get("code") == "agent_bad_credentials", result
    else:
        assert status == 200, result
        assert result.get("code") == "agent_bad_credentials", result
    assert _table_exists(table) is False
    # Token spent: replay still not_found (or credential gate 401).
    status2, again = _confirm(transport, audience.basic, token)
    assert status2 in {200, 401}, again
    if status2 == 200:
        assert again.get("code") in {
            "confirmation_not_found",
            "agent_bad_credentials",
        }, again


def test_temp_expiry_during_claim_lock_wait_denied() -> None:
    """Credential/challenge expires while waiting for claim lock; post-lock clock denies."""
    transport = "jsonrpc"
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    ready = threading.Barrier(2)
    outcomes: list[tuple[int, dict]] = []

    def holder() -> None:
        from app.core.security import hash_token

        engine = _engine()
        with engine.connect() as connection:
            connection.execute(
                text(
                    """
                    SELECT id FROM pending_confirmations
                    WHERE token_hash = :hash
                    FOR UPDATE
                    """
                ),
                {"hash": hash_token(token)},
            )
            ready.wait()
            connection.execute(
                text(
                    """
                    UPDATE pending_confirmations
                    SET expires_at = CURRENT_TIMESTAMP - interval '1 minute'
                    WHERE token_hash = :hash
                    """
                ),
                {"hash": hash_token(token)},
            )
            connection.execute(
                text(
                    """
                    UPDATE pond_tokens
                    SET expires_at = CURRENT_TIMESTAMP - interval '1 minute'
                    WHERE id = :id
                    """
                ),
                {"id": audience.token_id},
            )
            connection.commit()
        engine.dispose()

    def confirmer() -> None:
        ready.wait()
        outcomes.append(_confirm(transport, audience.basic, token))

    threads = [threading.Thread(target=holder), threading.Thread(target=confirmer)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert outcomes
    status, result = outcomes[0]
    assert status in {200, 401}, result
    if status == 401:
        assert result.get("code") == "agent_bad_credentials", result
    else:
        assert result.get("code") in {
            "confirmation_expired",
            "agent_bad_credentials",
            "confirmation_not_found",
        }, result
    assert _table_exists(table) is False


def test_temp_revoke_and_execute_linearization() -> None:
    """Revoke-before-admission denies; no later admission after a committed revoke."""
    transport = "jsonrpc"
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    # Path A: revoke wins the pond_token row lock first.
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE pond_tokens
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {"id": audience.token_id},
        )
    engine.dispose()

    status, denied = _confirm(transport, audience.basic, token)
    if status in {401, 403}:
        assert denied.get("code") == "agent_bad_credentials", denied
    else:
        assert status == 200, denied
        assert denied.get("code") == "agent_bad_credentials", denied
    assert _table_exists(table) is False

    # Path B: a fresh proposal cannot be issued after committed revoke.
    before = _pending_count()
    status, issue = _propose_write(transport, audience, _create_sql(table))
    _assert_gate_failure(status, issue, "agent_bad_credentials")
    assert _pending_count() == before


# --- Owner / temp boundary ---


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_cannot_confirm_any_owner_proposal(transport: str) -> None:
    audience = _seed_audience()
    ensure_demo_user()

    owner_propose = client.post(
        "/mcp",
        headers=_account_mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "create_pond",
            "params": {"name": _unique("ownerpond")},
        },
    )
    assert owner_propose.status_code == 200, owner_propose.text
    owner_token = owner_propose.json()["result"]["token"]

    status, denied = _confirm(transport, audience.basic, owner_token)
    assert status == 200, denied
    _assert_tool_error(denied, "confirmation_not_found")

    # Owner write SQL proposal also denied for temp.
    status, write = _mcp_call(
        "jsonrpc",
        _account_mcp_headers(),
        "run_sql",
        {
            "pond_name": audience.pond_name,
            "query": "SELECT 1",
            "mode": "write",
        },
    )
    # SELECT in write still proposes; use a real write shape.
    status, write = _mcp_call(
        "jsonrpc",
        _account_mcp_headers(),
        "run_sql",
        {
            "pond_name": audience.pond_name,
            "query": "CREATE TABLE app.owner_only_should_not_run (id integer)",
            "mode": "write",
        },
    )
    assert status == 200 and write.get("status") == "confirmation_required", write
    status, denied = _confirm(transport, audience.basic, write["token"])
    assert status == 200, denied
    _assert_tool_error(denied, "confirmation_not_found")


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_owner_routes_cannot_confirm_or_discard_temp_proposal(transport: str) -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)

    status, proposed = _propose_write(transport, audience, _create_sql(table))
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    rest = client.post(f"/api/v1/confirm/{token}", headers=audience.owner)
    assert rest.status_code == 404, rest.text
    assert rest.json().get("code") == "confirmation_not_found"

    discard = client.delete(f"/api/v1/confirm/{token}", headers=audience.owner)
    assert discard.status_code in {404, 204}, discard.text
    if discard.status_code == 404:
        assert discard.json().get("code") == "confirmation_not_found"

    status, mcp_denied = _confirm(transport, _account_mcp_headers(), token)
    assert status == 200, mcp_denied
    _assert_tool_error(mcp_denied, "confirmation_not_found")
    assert _table_exists(table) is False


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_failed_dispatch_does_not_rearm_token(transport: str) -> None:
    audience = _seed_audience()
    with psycopg.connect(_probe_admin_url(), autocommit=True) as conn:
        conn.execute(f"SELECT pg_stat_file('{COPY_MARKER}', true)")

    status, proposed = _propose_write(transport, audience, COPY_PROGRAM)
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    status, failed = _confirm(transport, audience.basic, token)
    assert status == 200, failed
    _assert_tool_error(failed, "sql_error")

    status, replay = _confirm(transport, audience.basic, token)
    assert status == 200, replay
    _assert_tool_error(replay, "confirmation_not_found")


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_non_sql_tools_still_forbidden(transport: str) -> None:
    audience = _seed_audience()
    for tool, arguments in (
        ("create_pond", {"name": _unique("nope")}),
        ("delete_pond", {"name": audience.pond_name}),
        ("stop_pond", {"name": audience.pond_name}),
        ("start_pond", {"name": audience.pond_name}),
        ("restore_backup", {"pond_name": audience.pond_name, "backup_id": str(uuid.uuid4())}),
        ("cancel_confirmation", {"token": "conf-fake"}),
        ("get_connection", {"name": audience.pond_name}),
    ):
        status, result = _mcp_call(transport, audience.basic, tool, arguments, rpc_id=tool)
        if status in {401, 403}:
            assert result.get("code") == "agent_disabled", (tool, result)
        else:
            assert status == 200, (tool, result)
            assert result.get("code") == "agent_disabled" or result.get("status") == "error", (
                tool,
                result,
            )


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_confirmation_requires_existing_run_sql_scope(transport: str) -> None:
    audience = _seed_audience(scopes=["whoami", "get_pond"])

    info = client.get("/mcp", headers=audience.basic)
    assert info.status_code == 200, info.text
    tools = set(info.json().get("read_only_tools", [])) | set(
        info.json().get("mutable_tools", [])
    )
    assert "confirm_action" not in tools
    assert "run_sql" not in tools

    status, denied = _mcp_call(
        transport,
        audience.basic,
        "confirm_action",
        {"token": "conf-fake"},
    )
    if status in {401, 403}:
        assert denied.get("code") == "agent_disabled", denied
    else:
        assert status == 200, denied
        assert denied.get("code") == "agent_disabled", denied


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_confirm_does_not_expand_sql_privileges(transport: str) -> None:
    audience = _seed_audience()
    marker = "/tmp/koicloud-temp-confirm-priv-marker"
    with psycopg.connect(_probe_admin_url(), autocommit=True) as conn:
        conn.execute(
            "SELECT 1 FROM pg_stat_file(%s, true)",
            (marker,),
        )

    query = f"COPY (SELECT 1) TO PROGRAM 'touch {marker}'"
    status, proposed = _propose_write(transport, audience, query)
    assert status == 200 and proposed.get("status") == "confirmation_required", proposed

    status, failed = _confirm(transport, audience.basic, proposed["token"])
    assert status == 200, failed
    _assert_tool_error(failed, "sql_error")
    with psycopg.connect(_probe_admin_url(), autocommit=True) as conn:
        present = conn.execute(
            "SELECT (pg_stat_file(%s, true)).size IS NOT NULL",
            (marker,),
        ).fetchone()
    assert present is not None and present[0] is False


def test_owner_confirmation_flows_regression() -> None:
    reset_pond_tables()
    ensure_demo_user()
    # Harness only: Micro defaults to max_ponds=1, but this regression exercises two
    # sequential owner creates (HTTP confirm + MCP confirm). Raise the cap without
    # changing the assertion matrix; restore afterward so plan seed tests stay green.
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(text("UPDATE plans SET max_ponds = 10 WHERE id = 'micro'"))
    engine.dispose()
    try:
        owner = _owner_headers()
        account = _account_mcp_headers()

        proposed = client.post(
            "/mcp",
            headers=account,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "create_pond",
                "params": {"name": _unique("regpond")},
            },
        )
        assert proposed.status_code == 200, proposed.text
        result = proposed.json()["result"]
        assert result["status"] == "confirmation_required"
        assert result["next"]["confirm_url"].startswith("/api/v1/confirm/")
        assert result["next"]["cli_example"].startswith("koicloud confirm ")

        confirmed = client.post(f"/api/v1/confirm/{result['token']}", headers=owner)
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["pond"]["name"].startswith("regpond")

        # Account MCP confirm_action path still works for owner proposals.
        proposed2 = client.post(
            "/mcp",
            headers=account,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "create_pond",
                "params": {"name": _unique("regpond2")},
            },
        )
        assert proposed2.status_code == 200, proposed2.text
        token2 = proposed2.json()["result"]["token"]
        status, mcp_ok = _confirm("jsonrpc", account, token2)
        assert status == 200, mcp_ok
        assert mcp_ok.get("pond", {}).get("name", "").startswith("regpond2"), mcp_ok
    finally:
        engine = _engine()
        with engine.begin() as connection:
            connection.execute(text("UPDATE plans SET max_ponds = 1 WHERE id = 'micro'"))
        engine.dispose()


@pytest.mark.asyncio
async def test_temp_internal_confirm_token_is_not_a_capability() -> None:
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    query = _create_sql(table)

    engine = _engine()
    with engine.begin() as connection:
        user_id = connection.execute(
            text("SELECT id FROM users WHERE email = :e"),
            {"e": DEMO_EMAIL},
        ).scalar_one()
    engine.dispose()

    actor_kwargs = {
        "user_id": str(user_id),
        "email": DEMO_EMAIL,
        "role": UserRole.CLIENT,
        "status": UserStatus.ACTIVE,
        "surface": AppSurface.MCP,
        "pond_id": audience.pond_id,
        "allowed_tools": frozenset({"whoami", "get_pond", "run_sql", "confirm_action"}),
    }
    if "pond_token_id" in AuthContext.model_fields:
        actor_kwargs["pond_token_id"] = audience.token_id
    actor = AuthContext(**actor_kwargs)

    from app.schemas import ConfirmationRequiredResponse

    try:
        result = await sql_commands.run_sql(
            uuid.UUID(audience.pond_id),
            RunSQLRequest(query=query, mode=SQLMode.WRITE),
            actor=actor,
            surface=AppSurface.MCP,
            confirm_token="conf-manufactured-not-a-grant",
        )
    except AppError as exc:
        assert exc.code in {
            ErrorCode.CONFIRMATION_NOT_FOUND,
            ErrorCode.CONFIRMATION_ACTION_MISMATCH,
            ErrorCode.AGENT_DISABLED,
        }
    else:
        # Manufactured truthy confirm_token must not authorize temp writes.
        assert isinstance(result, ConfirmationRequiredResponse), result
    assert _table_exists(table) is False


# --- Router decision / CCR: 401 vs 403 ---


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_suspended_owner_denied_401_at_all_admission_points(transport: str) -> None:
    """Temp credential with suspended/invalid owner → 401 agent_bad_credentials.

    Router decision (and CCR #96 TEMP-CONFIRM): not 403. Applies at gate, issue,
    claim and final admission. Does not change legacy full-account owner handling.
    """
    audience = _seed_audience()
    table = f"app.{_unique('t')}"
    _drop_table_if_exists(table)
    query = _create_sql(table)

    status, proposed = _propose_write(transport, audience, query)
    assert status == 200, proposed
    assert proposed.get("status") == "confirmation_required", proposed
    token = proposed["token"]

    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE users SET status = 'suspended' WHERE email = :email"),
            {"email": DEMO_EMAIL},
        )
    engine.dispose()

    gate = client.get("/mcp", headers=audience.basic)
    assert gate.status_code == 401, gate.text
    assert gate.json().get("code") == "agent_bad_credentials"

    confirm_status, confirm_body = _confirm(transport, audience.basic, token)
    assert confirm_status == 401, confirm_body
    assert confirm_body.get("code") == "agent_bad_credentials"

    issue_status, issue_body = _propose_write(
        transport, audience, _create_sql(f"app.{_unique('t')}")
    )
    assert issue_status == 401, issue_body
    assert issue_body.get("code") == "agent_bad_credentials"
    assert _table_exists(table) is False


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_temp_disabled_tool_scope_and_global_mcp_remain_403(transport: str) -> None:
    """Valid temp actor denied by tool, scope, or global MCP off → 403 agent_disabled."""
    audience = _seed_audience()
    # Forbidden tool while credential is live and owner active.
    status, body = _mcp_call(
        transport,
        audience.basic,
        "create_pond",
        {"name": _unique("x")},
    )
    if status in {401, 403}:
        _assert_gate_failure(status, body, "agent_disabled")
    else:
        _assert_tool_error(body, "agent_disabled")
        assert status == 200

    narrow = _seed_audience(scopes=["whoami", "get_pond"])
    status, body = _mcp_call(
        transport,
        narrow.basic,
        "confirm_action",
        {"token": "conf-no-scope"},
    )
    if status in {401, 403}:
        _assert_gate_failure(status, body, "agent_disabled")
    else:
        _assert_tool_error(body, "agent_disabled")

    audience2 = _seed_audience()
    settings = get_settings()
    previous = settings.mcp_enabled
    object.__setattr__(settings, "mcp_enabled", False)
    try:
        gate = client.get("/mcp", headers=audience2.basic)
        assert gate.status_code == 403, gate.text
        assert gate.json().get("code") == "agent_disabled"
    finally:
        object.__setattr__(settings, "mcp_enabled", previous)


# --- Migration binding checks ---


def test_pending_confirmations_temp_binding_columns_exist() -> None:
    engine = _engine()
    with engine.begin() as connection:
        cols = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'pending_confirmations'
                      AND column_name IN ('pond_token_id', 'pond_id', 'request_digest')
                    """
                )
            )
        }
    engine.dispose()
    assert cols == {"pond_token_id", "pond_id", "request_digest"}


def test_migration_upgrade_preserves_legacy_null_bound_rows() -> None:
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    matches = list(versions.glob("*temp_sql_confirmation*"))
    assert matches, "expected additive temp SQL confirmation binding migration"

    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO pending_confirmations (
                    id, user_id, token_hash, action, payload, summary, expires_at,
                    pond_token_id, pond_id, request_digest
                )
                SELECT
                    :id,
                    u.id,
                    :token_hash,
                    'create_pond',
                    '{}'::jsonb,
                    'legacy null-bound',
                    CURRENT_TIMESTAMP + interval '5 minutes',
                    NULL,
                    NULL,
                    NULL
                FROM users u
                WHERE u.email = :email
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "token_hash": f"legacy-{uuid.uuid4().hex}",
                "email": DEMO_EMAIL,
            },
        )
        row = connection.execute(
            text(
                """
                SELECT pond_token_id, pond_id, request_digest
                FROM pending_confirmations
                WHERE summary = 'legacy null-bound'
                ORDER BY expires_at DESC
                LIMIT 1
                """
            )
        ).first()
    engine.dispose()
    assert row is not None
    assert row.pond_token_id is None
    assert row.pond_id is None
    assert row.request_digest is None


def test_migration_downgrade_deletes_temp_bound_rows_first() -> None:
    """Downgrade must delete temp-bound rows before dropping binding columns."""
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    matches = list(versions.glob("*temp_sql_confirmation*"))
    assert matches, "expected additive temp SQL confirmation binding migration"
    source = matches[0].read_text(encoding="utf-8")
    assert "pond_token_id" in source
    assert "DELETE" in source.upper() or "delete(" in source
    # Behavioral check once columns exist: insert temp-bound row, simulate downgrade delete.
    audience = _seed_audience()
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO pending_confirmations (
                    id, user_id, token_hash, action, payload, summary, expires_at,
                    pond_token_id, pond_id, request_digest
                )
                SELECT
                    CAST(:id AS uuid),
                    u.id,
                    :token_hash,
                    'run_sql_write',
                    CAST(:payload AS jsonb),
                    'temp-bound-for-downgrade',
                    CURRENT_TIMESTAMP + interval '5 minutes',
                    CAST(:pond_token_id AS uuid),
                    CAST(:pond_id AS uuid),
                    :digest
                FROM users u
                WHERE u.email = :email
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "token_hash": f"temp-{uuid.uuid4().hex}",
                "payload": json.dumps(
                    {
                        "pond_id": audience.pond_id,
                        "request": {"query": "SELECT 1", "mode": "write"},
                    }
                ),
                "pond_token_id": audience.token_id,
                "pond_id": audience.pond_id,
                "digest": "a" * 64,
                "email": DEMO_EMAIL,
            },
        )
        deleted = connection.execute(
            text(
                """
                DELETE FROM pending_confirmations
                WHERE pond_token_id IS NOT NULL
                RETURNING id
                """
            )
        ).fetchall()
        assert deleted
        leftover = connection.execute(
            text(
                """
                SELECT count(*) FROM pending_confirmations
                WHERE summary = 'temp-bound-for-downgrade'
                """
            )
        ).scalar_one()
        assert int(leftover) == 0
    engine.dispose()
