from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@koicloud.dev", "password": "Sup3rSegura!2026"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_openapi_exposes_core_phase0_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/ponds" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/confirm/{token}" in paths
    assert "/internal/v1/jobs/claim" in paths
    assert "/mcp" in paths


def test_create_pond_requires_confirmation_for_cli_surface() -> None:
    response = client.post(
        "/api/v1/ponds",
        headers={**auth_headers(), "X-KOI-Surface": "cli"},
        json={"name": "inventario-demo"},
    )
    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "confirmation_required"
    assert body["next"]["cli_example"].startswith("koicloud confirm ")


def test_create_pond_web_happy_path_returns_queued_job() -> None:
    response = client.post(
        "/api/v1/ponds",
        headers=auth_headers(),
        json={"name": "inventario-demo"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["pond"]["name"] == "inventario-demo"
    assert body["pond"]["observed_state"] == "pending"
    assert body["job"]["type"] == "create_pond"
    assert body["job"]["status"] == "queued"
