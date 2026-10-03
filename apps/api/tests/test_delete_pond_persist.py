from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
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


def _create_running_pond() -> tuple[dict[str, str], str]:
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": "inventario-demo"})
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
    return headers, pond_id


def test_delete_pond_persists_job_and_marks_deleted() -> None:
    headers, pond_id = _create_running_pond()

    deleted = client.delete(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert deleted.status_code == 202
    body = deleted.json()
    assert body["pond"]["desired_state"] == "deleted"
    assert body["pond"]["observed_state"] == "deleting"
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["type"] == "backup_pond"
    assert body["jobs"][0]["status"] == "queued"

    listed = client.get("/api/v1/ponds", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["ponds"] == []

    claimed_backup = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed_backup.status_code == 200
    backup_job = claimed_backup.json()["job"]
    assert backup_job["type"] == "backup_pond"
    assert backup_job["payload"]["name"] == "inventario-demo"

    done_backup = client.post(
        f"/internal/v1/jobs/{backup_job['id']}/complete",
        headers=node_headers(),
        json={
            "status": "succeeded",
            "result": {
                "backup": {
                    "path": "/tmp/pre-delete.dump",
                    "size_bytes": 1,
                    "sha256": "d" * 64,
                }
            },
        },
    )
    assert done_backup.status_code == 204

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    job = claimed.json()["job"]
    assert job["type"] == "delete_pond"
    assert job["payload"]["name"] == "inventario-demo"

    done = client.post(
        f"/internal/v1/jobs/{job['id']}/complete",
        headers=node_headers(),
        json={"status": "succeeded", "result": {"deleted": True}},
    )
    assert done.status_code == 204

    missing = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert missing.status_code == 404


def test_retry_failed_job_requeues_last_failure() -> None:
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": "inventario-demo"})
    assert created.status_code == 202
    pond_id = created.json()["pond"]["id"]
    job_id = created.json()["job"]["id"]

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    failed = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=node_headers(),
        json={"status": "failed", "error": "boom"},
    )
    assert failed.status_code == 204

    retried = client.post(f"/api/v1/ponds/{pond_id}/retry", headers=headers)
    assert retried.status_code == 202
    body = retried.json()
    assert body["job"]["type"] == "create_pond"
    assert body["job"]["status"] == "queued"
    assert body["job"]["id"] != job_id


def test_root_health_aliases_api_health() -> None:
    root = client.get("/health")
    contract = client.get("/api/v1/health")
    assert root.status_code == 200
    assert contract.status_code == 200
    assert root.json()["ok"] is True
    assert contract.json()["ok"] is True
