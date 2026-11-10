"""CCR MCP-APPERROR-ENVELOPE: JSON-RPC tool errors use catalog messages only.

Organizing structure: actor × invoke path × failure class → observable wire.
Assert HTTP status, result.status/code/message, and that driver/override text
never appears. Nested/unknown fail closed. Gate 401/403 and Streamable stay
outside this envelope.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import ERROR_CATALOG, AppError, ErrorCode
from app.main import app
from app.mcp.server import mcp as mcp_server
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables
from tests.sql_probe_pond import seed_probe_pond

client = TestClient(app)
# Fail-closed paths re-raise into unexpected_error_handler; TestClient's default
# raise_server_exceptions=True surfaces that as a client exception even after the
# handler builds the HTTP 500 body. Observe the wire with this client.
fail_closed_client = TestClient(app, raise_server_exceptions=False)

LEAK = "INTERNAL_DRIVER_DETAIL_do_not_leak_xyz99"
INVOKE_PATHS = ("tools_call", "call_tool", "direct_alias")
ACTORS = ("owner", "temp")
STREAM_ACCEPT = "application/json, text/event-stream"

_STREAM_CLIENT: TestClient | None = None


def _stream_client() -> TestClient:
    """Streamable HTTP needs FastMCP lifespan (same pattern as TEMP-CONFIRM tests)."""
    global _STREAM_CLIENT
    if _STREAM_CLIENT is None:
        cm = TestClient(app)
        _STREAM_CLIENT = cm.__enter__()
    return _STREAM_CLIENT


def _basic(slug: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _owner_mcp_headers() -> dict[str, str]:
    ensure_demo_user()
    settings = get_settings()
    return _basic(settings.mcp_demo_slug, settings.mcp_demo_password)


def _owner_api_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _temp_mcp_headers() -> dict[str, str]:
    reset_pond_tables()
    pond = seed_probe_pond()
    owner = _owner_api_headers()
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    created = client.post(
        f"/api/v1/ponds/{pond.pond_id}/temp-access",
        headers=owner,
        json={
            "expires_at": expires_at,
            "scopes": ["whoami", "get_pond", "run_sql"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    return _basic(body["slug"], body["password"])


def _headers_for(actor: str) -> dict[str, str]:
    if actor == "owner":
        return _owner_mcp_headers()
    if actor == "temp":
        return _temp_mcp_headers()
    raise AssertionError(actor)


def _jsonrpc_body(invoke: str, tool: str, arguments: dict[str, Any], rpc_id: int = 1) -> dict:
    if invoke == "tools_call":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
    if invoke == "call_tool":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "call_tool",
            "params": {"name": tool, "arguments": arguments},
        }
    if invoke == "direct_alias":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": tool,
            "params": arguments,
        }
    raise AssertionError(invoke)


def _post_jsonrpc(
    headers: dict[str, str],
    body: dict,
    *,
    observe_server_errors: bool = False,
) -> Any:
    http = fail_closed_client if observe_server_errors else client
    return http.post("/mcp", headers=headers, json=body)


def _install_call_tool(monkeypatch: pytest.MonkeyPatch, side_effect: Any) -> None:
    async def _fake(tool_name: str, arguments: dict[str, Any]) -> Any:
        if callable(side_effect) and not isinstance(side_effect, BaseException):
            result = side_effect(tool_name, arguments)
            if isinstance(result, BaseException):
                raise result
            return result
        raise side_effect

    monkeypatch.setattr(mcp_server, "call_tool", _fake)


def _assert_no_leak(payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    assert LEAK not in text
    assert "INTERNAL_DRIVER" not in text


def _catalog_message(code: ErrorCode) -> str:
    return ERROR_CATALOG[code].message


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("invoke", INVOKE_PATHS)
def test_direct_apperror_uses_catalog_message_http_200(
    monkeypatch: pytest.MonkeyPatch, actor: str, invoke: str
) -> None:
    headers = _headers_for(actor)
    code = ErrorCode.SQL_ERROR
    _install_call_tool(
        monkeypatch,
        AppError(code, message=LEAK),
    )
    response = _post_jsonrpc(headers, _jsonrpc_body(invoke, "whoami", {}))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["error"] is None
    result = body["result"]
    assert result == {
        "status": "error",
        "code": code.value,
        "message": _catalog_message(code),
    }
    _assert_no_leak(body)


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("invoke", INVOKE_PATHS)
def test_immediate_cause_apperror_uses_catalog_message_http_200(
    monkeypatch: pytest.MonkeyPatch, actor: str, invoke: str
) -> None:
    headers = _headers_for(actor)
    code = ErrorCode.POND_NOT_FOUND
    app_error = AppError(code, message=LEAK)
    wrapped = RuntimeError("fastmcp-tool-error")
    wrapped.__cause__ = app_error
    _install_call_tool(monkeypatch, wrapped)
    response = _post_jsonrpc(headers, _jsonrpc_body(invoke, "whoami", {}))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["error"] is None
    result = body["result"]
    assert result == {
        "status": "error",
        "code": code.value,
        "message": _catalog_message(code),
    }
    _assert_no_leak(body)


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("invoke", INVOKE_PATHS)
def test_nested_apperror_fails_closed_no_unwrap(
    monkeypatch: pytest.MonkeyPatch, actor: str, invoke: str
) -> None:
    headers = _headers_for(actor)
    inner = AppError(ErrorCode.SQL_ERROR, message=LEAK)
    mid = RuntimeError("middle")
    mid.__cause__ = inner
    outer = RuntimeError("outer")
    outer.__cause__ = mid
    _install_call_tool(monkeypatch, outer)
    response = _post_jsonrpc(
        headers,
        _jsonrpc_body(invoke, "whoami", {}),
        observe_server_errors=True,
    )
    assert response.status_code == 500, response.text
    body = response.json()
    assert body["code"] == ErrorCode.INTERNAL_ERROR.value
    assert body["message"] == _catalog_message(ErrorCode.INTERNAL_ERROR)
    _assert_no_leak(body)


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("invoke", INVOKE_PATHS)
def test_unknown_exception_fails_closed(
    monkeypatch: pytest.MonkeyPatch, actor: str, invoke: str
) -> None:
    headers = _headers_for(actor)
    _install_call_tool(monkeypatch, RuntimeError(LEAK))
    response = _post_jsonrpc(
        headers,
        _jsonrpc_body(invoke, "whoami", {}),
        observe_server_errors=True,
    )
    assert response.status_code == 500, response.text
    body = response.json()
    assert body["code"] == ErrorCode.INTERNAL_ERROR.value
    assert body["message"] == _catalog_message(ErrorCode.INTERNAL_ERROR)
    _assert_no_leak(body)


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("invoke", INVOKE_PATHS)
def test_success_whoami_unchanged(actor: str, invoke: str) -> None:
    headers = _headers_for(actor)
    response = _post_jsonrpc(headers, _jsonrpc_body(invoke, "whoami", {}, rpc_id=42))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["error"] is None
    assert body["id"] == 42
    result = body["result"]
    assert "email" in result
    assert result.get("status") != "error"


def test_gate_401_unchanged_for_bad_credentials() -> None:
    ensure_demo_user()
    headers = _basic("demo-agent", "wrong-password")
    response = _post_jsonrpc(headers, _jsonrpc_body("tools_call", "whoami", {}))
    assert response.status_code == 401, response.text
    body = response.json()
    assert body["code"] == ErrorCode.AGENT_BAD_CREDENTIALS.value
    assert body["message"] == _catalog_message(ErrorCode.AGENT_BAD_CREDENTIALS)


def test_forbidden_tool_403_unchanged_for_temp_allowlist() -> None:
    headers = _temp_mcp_headers()
    response = _post_jsonrpc(
        headers,
        _jsonrpc_body("tools_call", "create_pond", {"name": f"x-{uuid.uuid4().hex[:8]}"}),
    )
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == ErrorCode.AGENT_DISABLED.value
    assert body["message"] == _catalog_message(ErrorCode.AGENT_DISABLED)


def test_streamable_http_remains_transport_native() -> None:
    """Streamable path bypasses the JSON-RPC envelope router; keep SSE wire."""
    headers = {
        **_owner_mcp_headers(),
        "Accept": STREAM_ACCEPT,
        "Content-Type": "application/json",
    }
    response = _stream_client().post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "whoami", "arguments": {}},
        },
    )
    assert response.status_code == 200, response.text
    content_type = response.headers.get("content-type", "")
    assert "text/event-stream" in content_type
    assert "data:" in response.text
    messages: list[dict] = []
    for block in response.text.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                messages.append(json.loads(line[5:].strip()))
    assert messages
    last = messages[-1]
    result = last.get("result") or {}
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        assert "email" in structured or "user_id" in structured
        assert structured.get("status") != "error"
    else:
        assert result.get("isError") is not True
        assert last.get("error") is None
