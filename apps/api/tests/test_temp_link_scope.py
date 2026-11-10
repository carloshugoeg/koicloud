"""P0: temp-access link stays scoped to its issued pond (HTTP + MCP).

Locks issue / use / expire / revoke misuse paths from the PondToken statechart.
Streamable HTTP must deny list_tables as agent_disabled (not NODE_UNAVAILABLE).
"""

from __future__ import annotations

import base64
import json
import threading
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

STREAM_ACCEPT = "application/json, text/event-stream"

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


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _owner_client() -> TestClient:
    return TestClient(app)


def _audience_client() -> TestClient:
    """Fresh client with no login cookies (refresh must not bleed)."""
    return TestClient(app)


def _basic(slug: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _owner_headers(owner: TestClient) -> dict[str, str]:
    ensure_demo_user()
    response = owner.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_running_pond(owner: TestClient, headers: dict[str, str], name: str | None = None) -> dict:
    pond_name = name or _unique("pond")
    created = owner.post("/api/v1/ponds", headers=headers, json={"name": pond_name})
    assert created.status_code == 202, created.text
    body = created.json()
    pond_id = body["pond"]["id"]
    job_id = body["job"]["id"]
    done = owner.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers={"X-Node-Token": get_settings().node_token},
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204, done.text
    return {"id": pond_id, "name": pond_name}


def _insert_second_pond(pond_a_id: str, name: str) -> dict:
    pond_b_id = str(uuid.uuid4())
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT user_id, plan_id, node_id, host_port, db_password_encrypted, engine_version
                FROM ponds WHERE id = :id
                """
            ),
            {"id": pond_a_id},
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
    return {"id": pond_b_id, "name": name}


def _create_temp_access(
    owner: TestClient,
    headers: dict[str, str],
    pond_id: str,
    *,
    expires_in_seconds: int = 3600,
) -> dict:
    expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in_seconds)).isoformat()
    response = owner.post(
        f"/api/v1/ponds/{pond_id}/temp-access",
        headers=headers,
        json={
            "expires_at": expires_at,
            "scopes": ["whoami", "get_pond", "run_sql"],
        },
    )
    return {"response": response, "body": response.json() if response.content else {}}


def _seed_temp_audience() -> tuple[dict, dict, dict]:
    reset_pond_tables()
    owner = _owner_client()
    headers = _owner_headers(owner)
    pond_a = _create_running_pond(owner, headers, name=_unique("alpha"))
    pond_b = _insert_second_pond(pond_a["id"], _unique("beta"))
    created = _create_temp_access(owner, headers, pond_a["id"])
    assert created["response"].status_code == 201, created["response"].text
    body = created["body"]
    basic = _basic(body["slug"], body["password"])
    return pond_a, pond_b, {
        "owner": owner,
        "headers": headers,
        "basic": basic,
        "slug": body["slug"],
        "password": body["password"],
        "token_id": body["id"],
    }


def _parse_sse_messages(raw: str) -> list[dict]:
    messages: list[dict] = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            messages.append(json.loads(line[5:].strip()))
    return messages


def _streamable_tool_error_text(result: dict) -> str:
    if result.get("isError"):
        bits = [
            part.get("text", "")
            for part in result.get("content") or []
            if isinstance(part, dict)
        ]
        return " ".join(bits)
    structured = result.get("structuredContent") or {}
    if isinstance(structured, dict):
        return str(structured.get("message") or structured.get("code") or structured)
    return str(result)


def test_temp_basic_rejected_on_non_pond_http_routes() -> None:
    """Temp Basic must not become an account session on /api/v1."""
    _pond_a, _pond_b, audience = _seed_temp_audience()
    aud = _audience_client()
    basic = audience["basic"]
    pond_id = _pond_a["id"]

    cases = [
        ("GET", "/api/v1/me", None),
        ("GET", "/api/v1/ponds", None),
        ("GET", f"/api/v1/ponds/{pond_id}", None),
        ("GET", "/api/v1/subscriptions", None),
        ("GET", "/api/v1/admin/users", None),
        ("POST", "/api/v1/auth/refresh", {}),
        (
            "POST",
            f"/api/v1/ponds/{pond_id}/temp-access",
            {
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "scopes": ["whoami"],
            },
        ),
    ]
    for method, path, body in cases:
        response = aud.request(method, path, headers=basic, json=body)
        payload = response.json()
        code = payload.get("code")
        if response.status_code == 404:
            assert code == "internal_error", (path, payload)
            continue
        assert response.status_code == 401, (path, response.status_code, response.text)
        assert code == "token_invalid", (path, payload)


def test_jsonrpc_out_of_allowlist_tools_return_agent_disabled() -> None:
    pond_a, _pond_b, audience = _seed_temp_audience()
    aud = _audience_client()
    basic = audience["basic"]
    for method, params in (
        ("list_tables", {"pond_id": pond_a["id"]}),
        ("get_usage", {}),
        ("list_subscriptions", {}),
    ):
        response = aud.post(
            "/mcp",
            headers=basic,
            json={
                "jsonrpc": "2.0",
                "id": method,
                "method": method,
                "params": params,
            },
        )
        assert response.status_code == 403, (method, response.text)
        assert response.json().get("code") == "agent_disabled", (method, response.text)


def test_streamable_list_tables_denied_as_agent_disabled() -> None:
    """Streamable HTTP must deny list_tables before any pond DB work."""
    pond_a, _pond_b, audience = _seed_temp_audience()
    client = _stream_client()
    response = client.post(
        "/mcp",
        headers={
            **audience["basic"],
            "Accept": STREAM_ACCEPT,
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_tables",
                "arguments": {"pond_id": pond_a["id"]},
            },
        },
    )
    if response.status_code in {401, 403}:
        assert response.json().get("code") == "agent_disabled", response.text
        return

    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers.get("content-type", ""), response.headers
    messages = _parse_sse_messages(response.text)
    assert messages, response.text
    result = messages[-1].get("result") or {}
    text = _streamable_tool_error_text(result).lower()
    structured = result.get("structuredContent") or {}
    code = structured.get("code") if isinstance(structured, dict) else None
    assert result.get("isError") is True or code == "agent_disabled", result
    assert code == "agent_disabled" or "desactivado" in text or "agent_disabled" in text, result
    assert "nodos" not in text, result
    assert "node_unavailable" not in text, result


def test_cross_pond_get_pond_denied() -> None:
    pond_a, pond_b, audience = _seed_temp_audience()
    aud = _audience_client()
    ok = aud.post(
        "/mcp",
        headers=audience["basic"],
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "get_pond",
            "params": {"name": pond_a["name"]},
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["result"]["pond"]["id"] == pond_a["id"]

    other = aud.post(
        "/mcp",
        headers=audience["basic"],
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_pond",
            "params": {"name": pond_b["name"]},
        },
    )
    assert other.status_code == 200, other.text
    result = other.json().get("result") or {}
    assert result.get("status") == "error", result
    assert result.get("code") == "pond_not_found", result
    assert "pond" not in result or result.get("pond") is None


def test_expired_temp_token_rejected_by_mcp() -> None:
    reset_pond_tables()
    owner = _owner_client()
    headers = _owner_headers(owner)
    pond = _create_running_pond(owner, headers)
    created = _create_temp_access(owner, headers, pond["id"], expires_in_seconds=-30)
    assert created["response"].status_code == 201, created["response"].text
    aud = _audience_client()
    denied = aud.get(
        "/mcp",
        headers=_basic(created["body"]["slug"], created["body"]["password"]),
    )
    assert denied.status_code == 401, denied.text
    assert denied.json().get("code") == "agent_bad_credentials", denied.text


def test_revoked_temp_token_rejected_by_mcp() -> None:
    reset_pond_tables()
    owner = _owner_client()
    headers = _owner_headers(owner)
    pond = _create_running_pond(owner, headers)
    created = _create_temp_access(owner, headers, pond["id"])
    assert created["response"].status_code == 201, created["response"].text
    body = created["body"]
    revoke = owner.post(
        f"/api/v1/ponds/{pond['id']}/temp-access/{body['id']}/revoke",
        headers=headers,
    )
    assert revoke.status_code == 200, revoke.text
    aud = _audience_client()
    denied = aud.get("/mcp", headers=_basic(body["slug"], body["password"]))
    assert denied.status_code == 401, denied.text
    assert denied.json().get("code") == "agent_bad_credentials", denied.text
