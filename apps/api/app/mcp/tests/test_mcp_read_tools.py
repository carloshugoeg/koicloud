from __future__ import annotations

import base64
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.main import app
from app.mcp.server import mcp
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

client = TestClient(app)

READ_ONLY = {
    "whoami",
    "list_ponds",
    "get_pond",
    "get_connection",
    "list_subscriptions",
    "list_backups",
    "get_usage",
}


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


def test_mcp_info_lists_seven_read_only_tools() -> None:
    ensure_demo_user()
    body = client.get("/mcp", headers=mcp_headers()).json()
    assert set(body["read_only_tools"]) == READ_ONLY
    assert "get_usage" in body["read_only_tools"]


@pytest.mark.asyncio
async def test_fastmcp_registers_seven_read_tools() -> None:
    names = {tool.name for tool in await mcp.list_tools()}
    assert READ_ONLY.issubset(names)


def test_mcp_list_subscriptions_shape() -> None:
    ensure_demo_user()
    result = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={"jsonrpc": "2.0", "id": 10, "method": "list_subscriptions", "params": {}},
    )
    assert result.status_code == 200
    payload = result.json()["result"]
    assert set(payload.keys()) == {"subscriptions", "next_cursor"}
    assert isinstance(payload["subscriptions"], list)


def test_mcp_get_usage_matches_usage_shape() -> None:
    ensure_demo_user()
    result = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={"jsonrpc": "2.0", "id": 13, "method": "get_usage", "params": {}},
    )
    assert result.status_code == 200
    payload = result.json()["result"]
    assert set(payload.keys()) == {
        "month",
        "total_instance_hours",
        "total_storage_gb_hours",
        "ponds",
    }
    assert isinstance(payload["ponds"], list)


def test_mcp_get_connection_and_list_backups() -> None:
    reset_pond_tables()
    ensure_demo_user()
    created = client.post(
        "/api/v1/ponds",
        headers=auth_headers(),
        json={"name": "mcp-read-pond"},
    )
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]

    connection = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 11,
            "method": "get_connection",
            "params": {"name": "mcp-read-pond"},
        },
    )
    assert connection.status_code == 200
    conn_body = connection.json()["result"]
    assert set(conn_body.keys()) == {"connection"}
    assert conn_body["connection"]["host"]

    backup_id = str(uuid4())
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as db:
        db.execute(
            text(
                """
                INSERT INTO backups (
                    id, pond_id, kind, status, storage_path, size_bytes, sha256, created_at
                )
                VALUES (
                    :id, :pond_id, 'on_demand', 'succeeded', '/tmp/demo.dump', 1, 'abc',
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {"id": backup_id, "pond_id": pond_id},
        )
    engine.dispose()

    backups = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 12,
            "method": "list_backups",
            "params": {"pond_name": "mcp-read-pond"},
        },
    )
    assert backups.status_code == 200
    backup_body = backups.json()["result"]
    assert set(backup_body.keys()) == {"backups", "next_cursor"}
    assert len(backup_body["backups"]) == 1
    assert backup_body["backups"][0]["id"] == backup_id
