from __future__ import annotations

import base64

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.security import verify_password
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_auth_tables

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_get_agent_access_persists_row() -> None:
    reset_auth_tables()
    ensure_demo_user()
    response = client.get("/api/v1/agent-access", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["slug"]
    assert body["enabled"] is True
    assert body["url"].endswith("/mcp")

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT access_slug, enabled FROM agent_access LIMIT 1")
        ).first()
    engine.dispose()
    assert row is not None
    assert row[0] == body["slug"]
    assert row[1] is True


def test_rotate_persists_argon2_and_gate_accepts_new_password() -> None:
    reset_auth_tables()
    ensure_demo_user()
    headers = auth_headers()

    rotated = client.post("/api/v1/agent-access/rotate", headers=headers)
    assert rotated.status_code == 200
    secret = rotated.json()
    slug = secret["slug"]
    password = secret["password"]
    assert password

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT password_hash FROM agent_access WHERE access_slug = :slug"),
            {"slug": slug},
        ).first()
    engine.dispose()
    assert row is not None
    assert verify_password(password, row[0])

    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    ok = client.get("/mcp", headers={"Authorization": f"Basic {token}"})
    assert ok.status_code == 200

    old = get_settings()
    old_token = base64.b64encode(
        f"{old.mcp_demo_slug}:{old.mcp_demo_password}".encode()
    ).decode("ascii")
    denied = client.get("/mcp", headers={"Authorization": f"Basic {old_token}"})
    assert denied.status_code == 401


def test_toggle_disables_gate() -> None:
    reset_auth_tables()
    ensure_demo_user()
    headers = auth_headers()

    rotated = client.post("/api/v1/agent-access/rotate", headers=headers)
    assert rotated.status_code == 200
    slug = rotated.json()["slug"]
    password = rotated.json()["password"]

    toggled = client.post(
        "/api/v1/agent-access/toggle",
        headers=headers,
        json={"enabled": False},
    )
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is False

    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    response = client.get("/mcp", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 403
    assert response.json()["code"] == "agent_disabled"
