from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

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


def test_mcp_info_requires_gate_and_lists_tools() -> None:
    ensure_demo_user()
    denied = client.get("/mcp")
    assert denied.status_code == 401

    ok = client.get("/mcp", headers=mcp_headers())
    assert ok.status_code == 200
    body = ok.json()
    assert body["endpoint"] == "/mcp"
    assert "whoami" in body["read_only_tools"]
    assert "confirm_action" in body["mutable_tools"]


def test_mcp_create_pond_propose_and_confirm() -> None:
    reset_pond_tables()
    ensure_demo_user()

    proposed = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={"jsonrpc": "2.0", "id": 1, "method": "create_pond", "params": {"name": "mcp-demo"}},
    )
    assert proposed.status_code == 200
    result = proposed.json()["result"]
    assert result["status"] == "confirmation_required"
    token = result["token"]
    assert token.startswith("conf-")

    confirmed = client.post(
        f"/api/v1/confirm/{token}",
        headers=auth_headers(),
    )
    assert confirmed.status_code == 200
    body = confirmed.json()
    assert body["pond"]["name"] == "mcp-demo"
    assert body["job"]["type"] == "create_pond"
    assert body["job"]["status"] == "queued"


def test_mcp_whoami_via_jsonrpc() -> None:
    ensure_demo_user()
    result = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={"jsonrpc": "2.0", "id": 2, "method": "whoami", "params": {}},
    )
    assert result.status_code == 200
    assert result.json()["result"]["email"] == DEMO_EMAIL
