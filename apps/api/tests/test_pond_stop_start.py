from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.security import hash_password
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

client = TestClient(app)

OTHER_EMAIL = "other-stop-start@koicloud.dev"
OTHER_PASSWORD = "Sup3rSegura!2026"


def auth_headers(email: str = DEMO_EMAIL, password: str = DEMO_PASSWORD) -> dict[str, str]:
    ensure_demo_user()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def node_headers() -> dict[str, str]:
    return {"X-Node-Token": get_settings().node_token}


def _ensure_other_user() -> None:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": OTHER_EMAIL},
        ).first()
        if existing is None:
            connection.execute(
                text(
                    """
                    INSERT INTO users (
                        id, email, password_hash, full_name, role, status, email_verified_at
                    )
                    VALUES (
                        :id, :email, :password_hash, :full_name, 'client', 'active', CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": str(uuid4()),
                    "email": OTHER_EMAIL,
                    "password_hash": hash_password(OTHER_PASSWORD),
                    "full_name": "Other User",
                },
            )
    engine.dispose()


def _create_running_pond(name: str = "inventario-demo") -> tuple[dict[str, str], str]:
    reset_pond_tables()
    headers = auth_headers()
    created = client.post("/api/v1/ponds", headers=headers, json={"name": name})
    assert created.status_code == 202, created.text
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


def _complete_job(job_id: str, *, status: str = "succeeded", result: dict | None = None) -> None:
    claimed = client.post("/internal/v1/jobs/claim", headers=node_headers(), json={})
    assert claimed.status_code == 200
    assert claimed.json()["job"]["id"] == job_id
    body: dict = {"status": status}
    if status == "succeeded":
        body["result"] = result or {}
    else:
        body["error"] = "boom"
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers=node_headers(),
        json=body,
    )
    assert done.status_code == 204


def test_stop_start_happy_path_and_transitions() -> None:
    headers, pond_id = _create_running_pond()

    stopped = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=headers)
    assert stopped.status_code == 202, stopped.text
    body = stopped.json()
    assert body["pond"]["desired_state"] == "stopped"
    assert body["pond"]["observed_state"] == "running"
    assert body["job"]["type"] == "stop_pond"
    assert body["job"]["status"] == "queued"

    _complete_job(body["job"]["id"], result={"observed_state": "stopped"})
    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["pond"]["desired_state"] == "stopped"
    assert detail.json()["pond"]["observed_state"] == "stopped"

    started = client.post(f"/api/v1/ponds/{pond_id}/start", headers=headers)
    assert started.status_code == 202, started.text
    start_body = started.json()
    assert start_body["pond"]["desired_state"] == "running"
    assert start_body["pond"]["observed_state"] == "stopped"
    assert start_body["job"]["type"] == "start_pond"

    _complete_job(start_body["job"]["id"], result={"observed_state": "running"})
    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert detail.json()["pond"]["desired_state"] == "running"
    assert detail.json()["pond"]["observed_state"] == "running"


def test_stop_start_409_wrong_state_and_in_flight() -> None:
    headers, pond_id = _create_running_pond()

    # start while running → pond_busy
    bad_start = client.post(f"/api/v1/ponds/{pond_id}/start", headers=headers)
    assert bad_start.status_code == 409
    assert bad_start.json()["code"] == "pond_busy"

    stopped = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=headers)
    assert stopped.status_code == 202
    job_id = stopped.json()["job"]["id"]

    # double-click / job in flight → pond_busy
    again = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=headers)
    assert again.status_code == 409
    assert again.json()["code"] == "pond_busy"
    start_while_stopping = client.post(f"/api/v1/ponds/{pond_id}/start", headers=headers)
    assert start_while_stopping.status_code == 409
    assert start_while_stopping.json()["code"] == "pond_busy"

    _complete_job(job_id, result={"observed_state": "stopped"})

    # stop while stopped → pond_busy
    bad_stop = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=headers)
    assert bad_stop.status_code == 409
    assert bad_stop.json()["code"] == "pond_busy"


def test_stop_404_and_403() -> None:
    headers, pond_id = _create_running_pond()
    missing = client.post(f"/api/v1/ponds/{uuid4()}/stop", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "pond_not_found"

    _ensure_other_user()
    other = auth_headers(OTHER_EMAIL, OTHER_PASSWORD)
    forbidden = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=other)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "not_owner"


def test_start_404_and_403() -> None:
    headers, pond_id = _create_running_pond()
    stopped = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=headers)
    assert stopped.status_code == 202
    _complete_job(stopped.json()["job"]["id"], result={"observed_state": "stopped"})

    missing = client.post(f"/api/v1/ponds/{uuid4()}/start", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "pond_not_found"

    _ensure_other_user()
    other = auth_headers(OTHER_EMAIL, OTHER_PASSWORD)
    forbidden = client.post(f"/api/v1/ponds/{pond_id}/start", headers=other)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "not_owner"


def test_stop_start_cli_confirmation_required() -> None:
    headers, pond_id = _create_running_pond()
    cli = {**headers, "X-KOI-Surface": "cli"}

    propose_stop = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=cli)
    assert propose_stop.status_code == 409
    assert propose_stop.json()["status"] == "confirmation_required"
    token = propose_stop.json()["token"]

    confirmed = client.post(f"/api/v1/confirm/{token}", headers=cli)
    assert confirmed.status_code == 200
    assert confirmed.json()["pond"]["desired_state"] == "stopped"
    assert confirmed.json()["job"]["type"] == "stop_pond"
    _complete_job(confirmed.json()["job"]["id"], result={"observed_state": "stopped"})

    propose_start = client.post(f"/api/v1/ponds/{pond_id}/start", headers=cli)
    assert propose_start.status_code == 409
    assert propose_start.json()["status"] == "confirmation_required"
    start_token = propose_start.json()["token"]
    confirmed_start = client.post(f"/api/v1/confirm/{start_token}", headers=cli)
    assert confirmed_start.status_code == 200
    assert confirmed_start.json()["job"]["type"] == "start_pond"


def test_stop_failure_sets_error_then_retry() -> None:
    headers, pond_id = _create_running_pond()
    stopped = client.post(f"/api/v1/ponds/{pond_id}/stop", headers=headers)
    assert stopped.status_code == 202
    job_id = stopped.json()["job"]["id"]
    _complete_job(job_id, status="failed")

    detail = client.get(f"/api/v1/ponds/{pond_id}", headers=headers)
    assert detail.json()["pond"]["desired_state"] == "stopped"
    assert detail.json()["pond"]["observed_state"] == "failed"

    # start needs observed=stopped → pond_busy while failed
    bad = client.post(f"/api/v1/ponds/{pond_id}/start", headers=headers)
    assert bad.status_code == 409
    assert bad.json()["code"] == "pond_busy"

    retried = client.post(f"/api/v1/ponds/{pond_id}/retry", headers=headers)
    assert retried.status_code == 202
    assert retried.json()["job"]["type"] == "stop_pond"
