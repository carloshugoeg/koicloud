from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def node_headers() -> dict[str, str]:
    return {"X-Node-Token": get_settings().node_token}


def _engine():
    return create_engine(to_sync_database_url(get_settings().database_url))


def _execute(statement: str, params: dict[str, object]) -> None:
    engine = _engine()
    with engine.begin() as db:
        db.execute(text(statement), params)
    engine.dispose()


def test_pond_size_bytes_is_null_then_latest_sample() -> None:
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": "size-demo"})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]
    assert created.json()["pond"]["size_bytes"] is None

    listed = client.get("/api/v1/ponds", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["ponds"][0]["size_bytes"] is None

    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["pond"]["size_bytes"] is None

    _execute(
        """
        INSERT INTO pond_samples (id, pond_id, size_bytes, container_state, sampled_at)
        VALUES
            (:older, :pond_id, 100, 'running', CURRENT_TIMESTAMP - INTERVAL '2 minutes'),
            (:newer, :pond_id, 250, 'running', CURRENT_TIMESTAMP - INTERVAL '1 minute')
        """,
        {"older": str(uuid4()), "newer": str(uuid4()), "pond_id": pond_id},
    )

    listed = client.get("/api/v1/ponds", headers=headers)
    assert listed.json()["ponds"][0]["size_bytes"] == 250
    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert detail.json()["pond"]["size_bytes"] == 250
    by_name = client.get("/api/v1/ponds/by-name/size-demo", headers=headers)
    assert by_name.status_code == 200
    assert by_name.json()["pond"]["size_bytes"] == 250


def test_admin_fields_totals_and_non_admin_forbidden() -> None:
    reset_pond_tables()
    headers = auth_headers()
    forbidden = client.get("/api/v1/admin/totals", headers=headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "admin_only"

    created = client.post("/api/v1/ponds", headers=headers, json={"name": "admin-size"})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]
    job_id = created.json()["job"]["id"]
    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=node_headers(),
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204

    _execute(
        """
        UPDATE pond_status SET last_error = :error WHERE pond_id = :pond_id
        """,
        {"error": "driver timeout", "pond_id": pond_id},
    )
    _execute(
        """
        INSERT INTO pond_samples (id, pond_id, size_bytes, container_state, sampled_at)
        VALUES (:id, :pond_id, 4096, 'running', CURRENT_TIMESTAMP)
        """,
        {"id": str(uuid4()), "pond_id": pond_id},
    )
    _execute(
        "UPDATE users SET role = 'admin' WHERE email = :email",
        {"email": DEMO_EMAIL},
    )
    admin = auth_headers()

    ponds = client.get("/api/v1/admin/ponds", headers=admin)
    assert ponds.status_code == 200
    match = next(row for row in ponds.json()["ponds"] if row["id"] == pond_id)
    assert match["size_bytes"] == 4096
    assert match["last_error"] == "driver timeout"

    totals = client.get("/api/v1/admin/totals", headers=admin)
    assert totals.status_code == 200
    body = totals.json()["totals"]
    assert body["users"] >= 1
    assert body["ponds"] >= 1
    running_before_delete = body["ponds_running"]
    ponds_before_delete = body["ponds"]
    assert running_before_delete >= 1

    _execute(
        "UPDATE ponds SET desired_state = 'deleted' WHERE id = :pond_id",
        {"pond_id": pond_id},
    )
    after = client.get("/api/v1/admin/totals", headers=admin).json()["totals"]
    assert after["ponds"] == ponds_before_delete - 1
    assert after["ponds_running"] == running_before_delete - 1
    assert after["users"] == body["users"]


def test_subscription_invoice_id_is_latest_or_null() -> None:
    reset_pond_tables()
    headers = auth_headers()
    user_id = client.get("/api/v1/me", headers=headers).json()["user"]["id"]
    bare_id = str(uuid4())
    _execute(
        """
        INSERT INTO subscriptions (
            id, user_id, plan_id, status,
            current_period_start, current_period_end, cancel_at_period_end
        )
        VALUES (
            :id, :user_id, 'micro', 'active',
            CURRENT_TIMESTAMP - INTERVAL '2 days',
            CURRENT_TIMESTAMP + INTERVAL '1 day',
            false
        )
        """,
        {"id": bare_id, "user_id": user_id},
    )

    subscribed = client.post(
        "/api/v1/subscriptions",
        headers=headers,
        json={"plan_id": "micro"},
    )
    assert subscribed.status_code == 202
    created_invoice = subscribed.json()["invoice"]["id"]
    assert subscribed.json()["subscription"]["invoice_id"] == created_invoice

    later_id = str(uuid4())
    sub_id = subscribed.json()["subscription"]["id"]
    _execute(
        """
        INSERT INTO invoices (
            id, number, user_id, subscription_id,
            subtotal_usd, iva_usd, total_usd, status, issued_at
        )
        VALUES (
            :id, :number, :user_id, :subscription_id,
            1, 0, 1, 'issued', CURRENT_TIMESTAMP + INTERVAL '1 day'
        )
        """,
        {
            "id": later_id,
            "number": f"KC-TEST-{later_id[:8]}",
            "user_id": user_id,
            "subscription_id": sub_id,
        },
    )

    listed = client.get("/api/v1/subscriptions", headers=headers)
    assert listed.status_code == 200
    by_id = {row["id"]: row for row in listed.json()["subscriptions"]}
    assert by_id[bare_id]["invoice_id"] is None
    assert by_id[sub_id]["invoice_id"] == later_id
