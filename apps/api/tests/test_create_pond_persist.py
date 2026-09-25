from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from tests.db_reset import reset_pond_tables

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@koicloud.dev", "password": "Sup3rSegura!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def node_headers() -> dict[str, str]:
    return {"X-Node-Token": get_settings().node_token}


def test_create_pond_persists_job_and_connection() -> None:
    reset_pond_tables()
    created = client.post(
        "/api/v1/ponds",
        headers=auth_headers(),
        json={"name": "inventario-demo"},
    )
    assert created.status_code == 202
    body = created.json()
    pond_id = body["pond"]["id"]
    assert body["pond"]["observed_state"] == "pending"
    assert body["pond"]["desired_state"] == "running"
    assert body["job"]["type"] == "create_pond"
    assert body["job"]["status"] == "queued"

    listed = client.get("/api/v1/ponds", headers=auth_headers())
    assert listed.status_code == 200
    assert listed.json()["ponds"][0]["id"] == pond_id

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    job = claimed.json()["job"]
    assert job["id"] == body["job"]["id"]
    assert job["payload"]["name"] == "inventario-demo"
    assert job["payload"]["db_password_plain"]

    empty = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert empty.status_code == 204

    done = client.post(
        f"/internal/v1/jobs/{job['id']}/complete",
        headers=node_headers(),
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204

    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=auth_headers())
    assert detail.status_code == 200
    assert detail.json()["pond"]["observed_state"] == "running"
    assert detail.json()["pond"]["healthy"] is True

    connection = client.get(f"/api/v1/ponds/{pond_id}/connection", headers=auth_headers())
    assert connection.status_code == 200
    uri = connection.json()["connection"]
    assert uri["username"] == "postgres"
    assert uri["database"] == "inventario_demo"
    assert uri["port"] == body["pond"]["host_port"]
    assert str(uri["port"]) in uri["uri"]


def test_create_pond_rejects_duplicate_name_and_quota() -> None:
    reset_pond_tables()
    headers = auth_headers()
    first = client.post("/api/v1/ponds", headers=headers, json={"name": "inventario-demo"})
    assert first.status_code == 202

    duplicate = client.post("/api/v1/ponds", headers=headers, json={"name": "inventario-demo"})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "pond_name_taken"

    quota = client.post("/api/v1/ponds", headers=headers, json={"name": "reportes-demo"})
    assert quota.status_code == 409
    assert quota.json()["code"] == "quota_exceeded"


def test_claim_without_jobs_returns_204() -> None:
    reset_pond_tables()
    response = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert response.status_code == 204
