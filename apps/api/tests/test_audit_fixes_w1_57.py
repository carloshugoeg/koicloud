"""W1-57 audit fixes: pond name rules, job password scrub, MCP bad-arg 4xx.

These assertions encode the demo-safe contract. On main they fail; the fix
commit must make them pass without editing this file.
"""

from __future__ import annotations

import base64
import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.security import hash_password
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

client = TestClient(app, raise_server_exceptions=False)
SHARED_NAME = "shared-demo-pond"


def _auth_headers(email: str = DEMO_EMAIL, password: str = DEMO_PASSWORD) -> dict[str, str]:
    ensure_demo_user()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _node_headers() -> dict[str, str]:
    return {"X-Node-Token": get_settings().node_token}


def _mcp_headers() -> dict[str, str]:
    ensure_demo_user()
    settings = get_settings()
    token = base64.b64encode(
        f"{settings.mcp_demo_slug}:{settings.mcp_demo_password}".encode()
    ).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _ensure_second_user(*, email: str, password: str = DEMO_PASSWORD) -> None:
    settings = get_settings()
    engine = create_engine(to_sync_database_url(settings.database_url))
    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email},
        ).first()
        if existing is None:
            user_id = str(uuid.uuid4())
            connection.execute(
                text(
                    """
                    INSERT INTO users (
                        id, email, password_hash, full_name, role, status,
                        email_verified_at, onboarded_at
                    )
                    VALUES (
                        :id, :email, :password_hash, :full_name, 'client', 'active',
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": user_id,
                    "email": email,
                    "password_hash": hash_password(password),
                    "full_name": "Other Demo",
                },
            )
        else:
            user_id = str(existing[0])
        connection.execute(
            text("DELETE FROM subscriptions WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO subscriptions (
                    id, user_id, plan_id, status,
                    current_period_start, current_period_end
                )
                VALUES (
                    :id, :user_id, 'micro', 'active',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 day'
                )
                """
            ),
            {"id": str(uuid.uuid4()), "user_id": user_id},
        )
    engine.dispose()


def _job_payload(job_id: str) -> dict[str, Any]:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT payload FROM jobs WHERE id = :id"),
            {"id": job_id},
        ).first()
    engine.dispose()
    assert row is not None
    payload = row[0]
    assert isinstance(payload, dict)
    return payload


def test_duplicate_pond_name_across_users_returns_409() -> None:
    reset_pond_tables()
    first = client.post(
        "/api/v1/ponds",
        headers=_auth_headers(),
        json={"name": SHARED_NAME},
    )
    assert first.status_code == 202, first.text

    other_email = f"other-{uuid.uuid4().hex[:8]}@koicloud.dev"
    _ensure_second_user(email=other_email)
    duplicate = client.post(
        "/api/v1/ponds",
        headers=_auth_headers(email=other_email),
        json={"name": SHARED_NAME},
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["code"] == "pond_name_taken"


def test_invalid_pond_name_returns_422() -> None:
    reset_pond_tables()
    response = client.post(
        "/api/v1/ponds",
        headers=_auth_headers(),
        json={"name": "Bad_Name!"},
    )
    assert response.status_code == 422, response.text


def test_job_payload_password_scrubbed_after_complete() -> None:
    reset_pond_tables()
    created = client.post(
        "/api/v1/ponds",
        headers=_auth_headers(),
        json={"name": "scrub-demo"},
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["job"]["id"]

    claimed = client.post("/internal/v1/jobs/claim", headers=_node_headers(), json={})
    assert claimed.status_code == 200, claimed.text
    plain = claimed.json()["job"]["payload"]["db_password_plain"]
    assert isinstance(plain, str) and plain and plain != "[redacted]"

    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=_node_headers(),
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204, done.text

    payload = _job_payload(job_id)
    stored = payload.get("db_password_plain")
    assert stored in (None, "[redacted]")
    assert plain not in str(payload)

    pond_id = created.json()["pond"]["id"]
    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=_auth_headers())
    assert detail.status_code == 200, detail.text
    assert detail.json()["pond"]["observed_state"] == "running"


def test_mcp_bad_argument_returns_4xx_not_500_jsonrpc() -> None:
    reset_pond_tables()
    response = client.post(
        "/mcp",
        headers=_mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "get_pond",
            "params": {"pond_name": "missing"},
        },
    )
    assert response.status_code < 500, response.text
    assert 400 <= response.status_code < 500, response.text
    body = response.json()
    error = body.get("error")
    assert isinstance(error, dict), body
    assert error.get("code") == -32602


def test_mcp_bad_argument_returns_4xx_or_rpc_invalid_params_streamable() -> None:
    reset_pond_tables()
    headers = {
        **_mcp_headers(),
        "Accept": "application/json, text/event-stream",
        "mcp-protocol-version": "2024-11-05",
    }
    with TestClient(app, raise_server_exceptions=False) as stream_client:
        response = stream_client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "get_pond", "arguments": {"pond_name": "missing"}},
            },
        )
    assert response.status_code != 500, response.text
    # Prefer HTTP 4xx; accept JSON-RPC invalid params (-32602) in the SSE body.
    if 400 <= response.status_code < 500:
        return
    assert "isError" in response.text or "-32602" in response.text, response.text
    assert "validation" in response.text.lower() or "-32602" in response.text
