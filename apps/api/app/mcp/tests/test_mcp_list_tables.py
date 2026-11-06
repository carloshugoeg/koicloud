"""MCP list_tables tool (issue #206)."""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.mcp.server import mcp
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user
from tests.schema_probe_pond import seed_schema_pond

client = TestClient(app)


def mcp_headers() -> dict[str, str]:
    settings = get_settings()
    token = base64.b64encode(
        f"{settings.mcp_demo_slug}:{settings.mcp_demo_password}".encode()
    ).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def auth_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_mcp_info_includes_list_tables() -> None:
    ensure_demo_user()
    body = client.get("/mcp", headers=mcp_headers()).json()
    assert "list_tables" in body["read_only_tools"]


async def test_fastmcp_registers_list_tables() -> None:
    names = {tool.name for tool in await mcp.list_tools()}
    assert "list_tables" in names


def test_mcp_list_tables_matches_http_schema() -> None:
    ensure_demo_user()
    pond = seed_schema_pond(with_tables=True)
    http = client.get(
        f"/api/v1/ponds/{pond.pond_id}/schema",
        headers=auth_headers(),
    )
    assert http.status_code == 200, http.text
    mcp_result = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 206,
            "method": "list_tables",
            "params": {"pond_id": str(pond.pond_id)},
        },
    )
    assert mcp_result.status_code == 200, mcp_result.text
    assert mcp_result.json()["result"] == http.json()
