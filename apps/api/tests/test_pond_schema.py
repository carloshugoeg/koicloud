"""API tests for GET /api/v1/ponds/{id}/schema (issue #206)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD
from tests.schema_probe_pond import (
    create_foreign_owner_pond,
    mark_pond_stopped,
    seed_schema_pond,
)

client = TestClient(app)


def _headers() -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_schema_empty_pond_returns_no_tables() -> None:
    pond = seed_schema_pond(with_tables=False)
    response = client.get(f"/api/v1/ponds/{pond.pond_id}/schema", headers=_headers())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"tables": []}


def test_schema_pond_with_two_tables() -> None:
    pond = seed_schema_pond(with_tables=True)
    response = client.get(f"/api/v1/ponds/{pond.pond_id}/schema", headers=_headers())
    assert response.status_code == 200, response.text
    tables = response.json()["tables"]
    names = sorted(table["name"] for table in tables)
    assert names == ["public.items", "public.orders"]
    for table in tables:
        assert "pg_catalog" not in table["name"]
        assert "information_schema" not in table["name"]


def test_schema_columns_types_nullable_default() -> None:
    pond = seed_schema_pond(with_tables=True)
    response = client.get(f"/api/v1/ponds/{pond.pond_id}/schema", headers=_headers())
    assert response.status_code == 200, response.text
    by_name = {table["name"]: table for table in response.json()["tables"]}
    orders = by_name["public.orders"]
    columns = {column["name"]: column for column in orders["columns"]}
    assert set(columns) == {"id", "label", "qty"}
    assert columns["id"]["nullable"] is False
    assert "int" in columns["id"]["type"].lower()
    assert columns["label"]["nullable"] is False
    assert columns["label"]["default"] is not None
    assert "x" in columns["label"]["default"]
    assert columns["qty"]["nullable"] is True
    assert columns["qty"]["default"] is None


def test_schema_row_estimate() -> None:
    pond = seed_schema_pond(with_tables=True)
    response = client.get(f"/api/v1/ponds/{pond.pond_id}/schema", headers=_headers())
    assert response.status_code == 200, response.text
    by_name = {table["name"]: table for table in response.json()["tables"]}
    assert by_name["public.orders"]["estimated_rows"] >= 2
    assert by_name["public.items"]["estimated_rows"] >= 1


def test_schema_unauthenticated_is_401() -> None:
    pond = seed_schema_pond(with_tables=False)
    response = client.get(f"/api/v1/ponds/{pond.pond_id}/schema")
    assert response.status_code == 401
    assert response.json()["code"] in {"token_invalid", "token_expired"}


def test_schema_missing_pond_is_404() -> None:
    missing = uuid4()
    response = client.get(f"/api/v1/ponds/{missing}/schema", headers=_headers())
    assert response.status_code == 404
    assert response.json()["code"] == "pond_not_found"


def test_schema_other_users_pond_is_denied() -> None:
    foreign, _email, _password = create_foreign_owner_pond()
    response = client.get(f"/api/v1/ponds/{foreign.pond_id}/schema", headers=_headers())
    assert response.status_code in {403, 404}
    assert response.json()["code"] in {"not_owner", "pond_not_found"}


def test_schema_stopped_pond_is_clear_error() -> None:
    pond = seed_schema_pond(with_tables=False)
    mark_pond_stopped(pond.pond_id)
    response = client.get(f"/api/v1/ponds/{pond.pond_id}/schema", headers=_headers())
    assert response.status_code in {409, 503}
    assert response.json()["code"] in {"pond_busy", "node_unavailable"}
