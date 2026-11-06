"""Phase 1 tests for issue #204 — console MCP snippets (Claude / Cursor / Codex).

Acceptance criteria and console-mcp-connect statechart:
- documented config snippet per client authenticates with temp link + password
- smoke per client calls whoami or get_pond and stays pond-pinned
- auth fail stays denied
- forbidden / off-pond stay denied while pinned

No production code in this commit: imports and docs paths must fail until Phase 2.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "demo-console-mcp.md"
CLIENTS = ("claude_code", "cursor_cli", "codex_cli")


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def auth_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_running_pond(headers: dict[str, str], name: str | None = None) -> dict:
    pond_name = name or _unique("pond")
    created = client.post("/api/v1/ponds", headers=headers, json={"name": pond_name})
    assert created.status_code == 202, created.text
    body = created.json()
    pond_id = body["pond"]["id"]
    job_id = body["job"]["id"]
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers={"X-Node-Token": get_settings().node_token},
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204, done.text
    return {"id": pond_id, "name": pond_name}


def _create_temp_access(headers: dict[str, str], pond_id: str) -> dict:
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    response = client.post(
        f"/api/v1/ponds/{pond_id}/temp-access",
        headers=headers,
        json={"expires_at": expires_at, "scopes": ["whoami", "get_pond", "run_sql"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _issue_creds() -> tuple[dict, dict]:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    secret = _create_temp_access(headers, pond["id"])
    return pond, secret


def test_console_snippet_module_exports_three_clients() -> None:
    """Registry names the three console agents from the issue title."""
    from app.mcp.console_snippets import CONSOLE_CLIENTS, build_snippet

    assert set(CONSOLE_CLIENTS) == set(CLIENTS)
    for name in CLIENTS:
        text = build_snippet(
            name,
            url="https://koicloud.local/mcp",
            slug="pond-demo",
            password="secret",
        )
        assert isinstance(text, str)
        assert text.strip()


@pytest.mark.parametrize("client_id", CLIENTS)
def test_snippet_headers_authenticate_whoami_and_stay_pond_pinned(client_id: str) -> None:
    """Paste → auth ok → whoami; get_pond only for the pinned pond (statechart)."""
    from app.mcp.console_snippets import build_snippet, headers_from_snippet

    pond, secret = _issue_creds()
    snippet = build_snippet(
        client_id,
        url=secret["url"],
        slug=secret["slug"],
        password=secret["password"],
    )
    mcp_headers = headers_from_snippet(client_id, snippet)
    assert "Authorization" in mcp_headers

    who = client.post(
        "/mcp",
        headers=mcp_headers,
        json={"jsonrpc": "2.0", "id": 1, "method": "whoami", "params": {}},
    )
    assert who.status_code == 200, who.text
    assert who.json()["result"]["email"] == DEMO_EMAIL

    pinned = client.post(
        "/mcp",
        headers=mcp_headers,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_pond",
            "params": {"name": pond["name"]},
        },
    )
    assert pinned.status_code == 200, pinned.text
    assert pinned.json()["result"]["pond"]["id"] == pond["id"]

    info = client.get("/mcp", headers=mcp_headers)
    assert info.status_code == 200, info.text
    tools = set(info.json().get("read_only_tools", [])) | set(
        info.json().get("mutable_tools", [])
    )
    assert "whoami" in tools
    assert "get_pond" in tools
    assert "create_pond" not in tools
    assert "list_tables" not in tools


@pytest.mark.parametrize("client_id", CLIENTS)
def test_wrong_password_in_snippet_returns_401(client_id: str) -> None:
    """Auth fail path: pasted wrong password never pond-pins."""
    from app.mcp.console_snippets import build_snippet, headers_from_snippet

    _pond, secret = _issue_creds()
    snippet = build_snippet(
        client_id,
        url=secret["url"],
        slug=secret["slug"],
        password="not-the-password",
    )
    mcp_headers = headers_from_snippet(client_id, snippet)
    denied = client.get("/mcp", headers=mcp_headers)
    assert denied.status_code == 401
    assert denied.json().get("code") == "agent_bad_credentials"


@pytest.mark.parametrize("client_id", CLIENTS)
def test_forbidden_tool_denied_while_pinned(client_id: str) -> None:
    """Forbidden tool denied; session remains usable for whoami."""
    from app.mcp.console_snippets import build_snippet, headers_from_snippet

    _pond, secret = _issue_creds()
    snippet = build_snippet(
        client_id,
        url=secret["url"],
        slug=secret["slug"],
        password=secret["password"],
    )
    mcp_headers = headers_from_snippet(client_id, snippet)

    bad = client.post(
        "/mcp",
        headers=mcp_headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "create_pond",
            "params": {"name": _unique("nope")},
        },
    )
    assert bad.status_code in {200, 403}
    body = bad.json()
    if bad.status_code == 200:
        err = body.get("error") or body.get("result") or {}
        assert isinstance(err, dict)
        assert err.get("status") == "error" or err.get("code") in {
            "agent_disabled",
            "forbidden",
        }

    who = client.post(
        "/mcp",
        headers=mcp_headers,
        json={"jsonrpc": "2.0", "id": 4, "method": "whoami", "params": {}},
    )
    assert who.status_code == 200, who.text
    assert who.json()["result"]["email"] == DEMO_EMAIL


def test_runbook_documents_each_console_client_snippet() -> None:
    """Documented config snippet exists per client (acceptance criteria 1–3)."""
    assert RUNBOOK.is_file(), f"missing runbook {RUNBOOK}"
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "Claude Code" in text
    assert "Cursor CLI" in text or "Cursor" in text
    assert "Codex CLI" in text or "Codex" in text
    assert "claude mcp add" in text
    assert "mcpServers" in text
    assert "mcp_servers" in text
    assert re.search(r"Authorization", text)


def test_basic_authorization_matches_snippet_headers() -> None:
    """headers_from_snippet yields the same Basic token the gate expects."""
    from app.mcp.console_snippets import basic_authorization, build_snippet, headers_from_snippet

    slug = "pond-abc"
    password = "s3cret"
    expected = basic_authorization(slug, password)
    raw = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    assert expected == f"Basic {raw}"

    for client_id in CLIENTS:
        snippet = build_snippet(
            client_id,
            url="https://example.test/mcp",
            slug=slug,
            password=password,
        )
        headers = headers_from_snippet(client_id, snippet)
        assert headers["Authorization"] == expected


def test_cursor_snippet_is_valid_json() -> None:
    from app.mcp.console_snippets import build_snippet

    snippet = build_snippet(
        "cursor_cli",
        url="https://example.test/mcp",
        slug="pond-x",
        password="p",
    )
    parsed = json.loads(snippet)
    assert "mcpServers" in parsed
    assert "koicloud" in parsed["mcpServers"]
    assert parsed["mcpServers"]["koicloud"]["url"] == "https://example.test/mcp"
