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
    assert "restore_backup" in body["mutable_tools"]
    assert "run_sql" in body["mutable_tools"]


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


def test_mcp_gate_rejects_bad_password() -> None:
    ensure_demo_user()
    token = base64.b64encode(b"demo-agent:wrong-password").decode("ascii")
    response = client.get("/mcp", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "agent_bad_credentials"


def test_mcp_delete_summary_includes_state_and_pre_delete() -> None:
    reset_pond_tables()
    ensure_demo_user()
    created = client.post(
        "/api/v1/ponds",
        headers=auth_headers(),
        json={"name": "para-borrar"},
    )
    assert created.status_code == 202

    proposed = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "delete_pond",
            "params": {"name": "para-borrar"},
        },
    )
    assert proposed.status_code == 200
    summary = proposed.json()["result"]["summary"]
    assert "para-borrar" in summary
    assert "pre_delete" in summary
    assert "estado:" in summary


def test_mcp_restore_and_run_sql_write_require_confirmation() -> None:
    reset_pond_tables()
    ensure_demo_user()
    created = client.post(
        "/api/v1/ponds",
        headers=auth_headers(),
        json={"name": "sql-pond"},
    )
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]

    # Insert a succeeded backup directly — create_pond job still holds pond_busy.
    from uuid import uuid4

    from sqlalchemy import create_engine, text

    from app.core.config import to_sync_database_url

    backup_id = str(uuid4())
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        connection.execute(
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

    restore = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "restore_backup",
            "params": {"pond_name": "sql-pond", "backup_id": backup_id},
        },
    )
    assert restore.status_code == 200
    assert restore.json()["result"]["status"] == "confirmation_required"
    assert "restaurará" in restore.json()["result"]["summary"]

    write = client.post(
        "/mcp",
        headers=mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "run_sql",
            "params": {
                "pond_name": "sql-pond",
                "query": "DELETE FROM t",
                "mode": "write",
            },
        },
    )
    assert write.status_code == 200
    assert write.json()["result"]["status"] == "confirmation_required"


def test_mcp_streamable_initialize_via_hybrid() -> None:
    ensure_demo_user()
    with TestClient(app) as stream_client:
        response = stream_client.post(
            "/mcp",
            headers={
                **mcp_headers(),
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "koi-test", "version": "0"},
                },
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "serverInfo" in response.text
