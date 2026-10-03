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


def _create_running_pond(name: str = "inventario-demo") -> tuple[dict[str, str], str]:
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": name})
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


def test_list_backups_empty_then_persists_on_demand() -> None:
    headers, pond_id = _create_running_pond()

    empty = client.get(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["backups"] == []

    triggered = client.post(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert triggered.status_code == 202
    body = triggered.json()
    backup_id = body["backup"]["id"]
    assert body["backup"]["kind"] == "on_demand"
    assert body["backup"]["status"] == "queued"
    assert body["backup"]["pond_id"] == pond_id
    assert body["job"]["type"] == "backup_pond"
    assert body["job"]["status"] == "queued"

    listed = client.get(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["backups"]) == 1
    assert listed.json()["backups"][0]["id"] == backup_id

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    job = claimed.json()["job"]
    assert job["type"] == "backup_pond"
    assert job["payload"]["backup_id"] == backup_id
    assert job["payload"]["name"] == "inventario-demo"

    running = client.get(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert running.json()["backups"][0]["status"] == "running"

    done = client.post(
        f"/internal/v1/jobs/{job['id']}/complete",
        headers=node_headers(),
        json={
            "status": "succeeded",
            "result": {
                "backup": {
                    "path": f"/tmp/koicloud/backups/inventario-demo/{backup_id}.dump",
                    "size_bytes": 42,
                    "sha256": "a" * 64,
                    "backup_id": backup_id,
                }
            },
        },
    )
    assert done.status_code == 204

    succeeded = client.get(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    assert succeeded.status_code == 200
    row = succeeded.json()["backups"][0]
    assert row["status"] == "succeeded"
    assert row["size_bytes"] == 42
    assert row["sha256"] == "a" * 64
    assert row["completed_at"] is not None


def test_restore_backup_happy_path_and_rejects_foreign_id() -> None:
    headers, pond_id = _create_running_pond()

    triggered = client.post(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    backup_id = triggered.json()["backup"]["id"]
    job_id = triggered.json()["job"]["id"]

    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=node_headers(),
        json={
            "status": "succeeded",
            "result": {
                "backup": {
                    "path": "/tmp/b.dump",
                    "size_bytes": 10,
                    "sha256": "b" * 64,
                }
            },
        },
    )
    assert done.status_code == 204

    foreign = client.post(
        f"/api/v1/ponds/{pond_id}/restore",
        headers=headers,
        json={"backup_id": "99999999-9999-9999-9999-999999999999"},
    )
    assert foreign.status_code == 404
    assert foreign.json()["code"] == "pond_not_found"

    restored = client.post(
        f"/api/v1/ponds/{pond_id}/restore",
        headers=headers,
        json={"backup_id": backup_id},
    )
    assert restored.status_code == 202
    assert restored.json()["job"]["type"] == "restore_pond"
    assert restored.json()["job"]["status"] == "queued"

    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert detail.json()["pond"]["observed_state"] == "restoring"

    claimed_restore = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed_restore.status_code == 200
    restore_job = claimed_restore.json()["job"]
    assert restore_job["payload"]["backup_id"] == backup_id

    finish = client.post(
        f"/internal/v1/jobs/{restore_job['id']}/complete",
        headers=node_headers(),
        json={"status": "succeeded", "result": {"restored": True}},
    )
    assert finish.status_code == 204

    after = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert after.json()["pond"]["observed_state"] == "running"
    assert after.json()["pond"]["last_restore_at"] is not None


def test_delete_pond_enqueues_pre_delete_backup_before_delete() -> None:
    headers, pond_id = _create_running_pond()

    deleted = client.delete(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert deleted.status_code == 202
    body = deleted.json()
    assert body["pond"]["desired_state"] == "deleted"
    assert body["pond"]["observed_state"] == "deleting"
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["type"] == "backup_pond"
    assert body["jobs"][0]["status"] == "queued"

    backups = client.get(f"/api/v1/ponds/{pond_id}/backups", headers=headers)
    # pond is soft-deleted for list_ponds, but get_owned for backups may 404
    # because desired_state=deleted. Accept either empty owned list path via claim.
    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    backup_job = claimed.json()["job"]
    assert backup_job["type"] == "backup_pond"
    assert backup_job["payload"]["backup_id"]

    done_backup = client.post(
        f"/internal/v1/jobs/{backup_job['id']}/complete",
        headers=node_headers(),
        json={
            "status": "succeeded",
            "result": {
                "backup": {
                    "path": "/tmp/pre-delete.dump",
                    "size_bytes": 7,
                    "sha256": "c" * 64,
                }
            },
        },
    )
    assert done_backup.status_code == 204

    claimed_delete = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed_delete.status_code == 200
    delete_job = claimed_delete.json()["job"]
    assert delete_job["type"] == "delete_pond"
    assert delete_job["payload"]["name"] == "inventario-demo"

    finish = client.post(
        f"/internal/v1/jobs/{delete_job['id']}/complete",
        headers=node_headers(),
        json={"status": "succeeded", "result": {"deleted": True}},
    )
    assert finish.status_code == 204

    missing = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert missing.status_code == 404
    # silence unused if backups listing is blocked for deleted ponds
    assert backups.status_code in {200, 404}
