"""Phase 1 tests for issue #203 — pond-scoped temporary access.

One test per statechart transition (and HTTP status). No production code yet:
these must fail until Phase 2 implements create/list/revoke + MCP pin.
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.security import verify_password
from app.main import app
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables

client = TestClient(app)


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def auth_headers() -> dict[str, str]:
    ensure_demo_user()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_running_pond(headers: dict[str, str], name: str | None = None) -> dict:
    pond_name = name or _unique("pond")
    created = client.post("/api/v1/ponds", headers=headers, json={"name": pond_name})
    assert created.status_code == 202, created.text
    body = created.json()
    pond_id = body["pond"]["id"]
    job_id = body["job"]["id"]
    done = client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers={"X-Node-Token": get_settings().node_token},
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204, done.text
    return {"id": pond_id, "name": pond_name}


def _basic(slug: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


DEFAULT_TEMP_SCOPES = {"whoami", "list_ponds", "get_pond", "run_sql"}


def _create_temp_access(
    headers: dict[str, str],
    pond_id: str,
    *,
    expires_in_seconds: int = 3600,
) -> dict:
    return _post_temp_access(
        headers,
        pond_id,
        scopes=["whoami", "get_pond", "run_sql"],
        expires_in_seconds=expires_in_seconds,
    )


def _post_temp_access(
    headers: dict[str, str] | None,
    pond_id: str,
    *,
    scopes: object | None = None,
    include_scopes: bool = True,
    expires_in_seconds: int = 3600,
) -> dict:
    expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in_seconds)).isoformat()
    payload: dict = {"expires_at": expires_at}
    if include_scopes:
        payload["scopes"] = scopes
    response = client.post(
        f"/api/v1/ponds/{pond_id}/temp-access",
        headers=headers or {},
        json=payload,
    )
    return {"response": response, "body": response.json() if response.content else {}}


def _count_pond_tokens(pond_id: str) -> int:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM pond_tokens WHERE pond_id = :pond_id"),
            {"pond_id": pond_id},
        ).scalar_one()
    engine.dispose()
    return int(count)


def _assert_scopes_validation_422(response, *, require_value_error: bool = True) -> None:
    assert response.status_code == 422, response.text
    body = response.json()
    detail = body.get("detail")
    assert isinstance(detail, list) and detail, body
    scopes_entries = [
        item
        for item in detail
        if isinstance(item, dict) and "scopes" in (item.get("loc") or [])
    ]
    assert scopes_entries, body
    if require_value_error:
        assert any(
            "value_error" in str(item.get("type", "")) for item in scopes_entries
        ), body
    assert "password" not in body
    assert "slug" not in body


# --- issued ---


def test_create_returns_one_time_password_and_stores_only_hash() -> None:
    """Issued: plaintext returned once; DB keeps only the hash."""
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _create_temp_access(headers, pond["id"])
    assert created["response"].status_code == 201, created["response"].text
    body = created["body"]
    assert body.get("password"), body
    assert body.get("id"), body
    assert body.get("slug") or body.get("url"), body
    assert "password_hash" not in body

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT password_hash, expires_at, revoked_at, scopes, pond_id
                FROM pond_tokens
                WHERE id = :id
                """
            ),
            {"id": body["id"]},
        ).first()
        plaintext_cols = connection.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'pond_tokens' AND column_name IN ('password', 'plaintext')
                """
            )
        ).fetchall()
    engine.dispose()
    assert row is not None
    assert str(row.pond_id) == pond["id"]
    assert row.revoked_at is None
    assert row.expires_at is not None
    assert verify_password(body["password"], row.password_hash)
    assert plaintext_cols == []


def test_list_shows_metadata_without_plaintext_password() -> None:
    """Issued → list: metadata only, never the password."""
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _create_temp_access(headers, pond["id"])
    assert created["response"].status_code == 201, created["response"].text
    token_id = created["body"]["id"]
    password = created["body"]["password"]

    listed = client.get(f"/api/v1/ponds/{pond['id']}/temp-access", headers=headers)
    assert listed.status_code == 200, listed.text
    items = listed.json().get("tokens") or listed.json()
    assert isinstance(items, list)
    match = next(item for item in items if item["id"] == token_id)
    assert match["pond_id"] == pond["id"]
    assert "expires_at" in match
    assert match.get("revoked_at") in (None, )
    assert "scopes" in match
    assert "password" not in match
    assert password not in listed.text


# --- revoke / expire ---


def test_revoke_sets_revoked_at_and_mcp_auth_fails_401() -> None:
    """Active/Issued → Revoked; use after revoke → 401."""
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _create_temp_access(headers, pond["id"])
    assert created["response"].status_code == 201, created["response"].text
    token_id = created["body"]["id"]
    slug = created["body"]["slug"]
    password = created["body"]["password"]

    before = client.get("/mcp", headers=_basic(slug, password))
    assert before.status_code == 200, before.text

    revoked = client.post(
        f"/api/v1/ponds/{pond['id']}/temp-access/{token_id}/revoke",
        headers=headers,
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json().get("revoked_at")

    after = client.get("/mcp", headers=_basic(slug, password))
    assert after.status_code == 401
    assert after.json().get("code") in {"agent_bad_credentials", "token_invalid", "agent_disabled"}


def test_expired_token_rejected_by_mcp_auth_401() -> None:
    """Issued/Active → Expired; use after expiry → 401."""
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _create_temp_access(headers, pond["id"], expires_in_seconds=-30)
    assert created["response"].status_code == 201, created["response"].text
    slug = created["body"]["slug"]
    password = created["body"]["password"]

    denied = client.get("/mcp", headers=_basic(slug, password))
    assert denied.status_code == 401
    assert denied.json().get("code") in {"agent_bad_credentials", "token_expired", "token_invalid"}


# --- active / pin ---


def test_valid_token_authenticates_mcp_and_pins_to_pond() -> None:
    """Issued → Active: MCP whoami works; get_pond only for the pinned pond."""
    reset_pond_tables()
    headers = auth_headers()
    pond_a = _create_running_pond(headers, name=_unique("alpha"))
    # Micro plan max_ponds=1: insert a second owned pond directly so the pin
    # assertion can compare two real ponds without hitting quota_exceeded.
    pond_b_name = _unique("beta")
    pond_b_id = str(uuid.uuid4())
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT user_id, plan_id, node_id, host_port, db_password_encrypted, engine_version
                FROM ponds WHERE id = :id
                """
            ),
            {"id": pond_a["id"]},
        ).one()
        connection.execute(
            text(
                """
                INSERT INTO ponds (
                    id, user_id, plan_id, node_id, name, engine_version,
                    desired_state, host_port, db_password_encrypted, created_at
                ) VALUES (
                    :id, :user_id, :plan_id, :node_id, :name, :engine_version,
                    'running', :host_port, :db_password_encrypted, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": pond_b_id,
                "user_id": row.user_id,
                "plan_id": row.plan_id,
                "node_id": row.node_id,
                "name": pond_b_name,
                "engine_version": row.engine_version,
                "host_port": int(row.host_port) + 1,
                "db_password_encrypted": row.db_password_encrypted,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO pond_status (pond_id, observed_state, healthy)
                VALUES (:id, 'running', true)
                """
            ),
            {"id": pond_b_id},
        )
    engine.dispose()
    pond_b = {"id": pond_b_id, "name": pond_b_name}
    created = _create_temp_access(headers, pond_a["id"])
    assert created["response"].status_code == 201, created["response"].text
    slug = created["body"]["slug"]
    password = created["body"]["password"]
    mcp = _basic(slug, password)

    info = client.get("/mcp", headers=mcp)
    assert info.status_code == 200, info.text
    tools = set(info.json().get("read_only_tools", [])) | set(info.json().get("mutable_tools", []))
    assert "whoami" in tools
    assert "get_pond" in tools
    assert "run_sql" in tools
    assert "create_pond" not in tools
    assert "delete_pond" not in tools

    who = client.post(
        "/mcp",
        headers=mcp,
        json={"jsonrpc": "2.0", "id": 1, "method": "whoami", "params": {}},
    )
    assert who.status_code == 200, who.text
    assert who.json()["result"]["email"] == DEMO_EMAIL

    ok_pond = client.post(
        "/mcp",
        headers=mcp,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_pond",
            "params": {"name": pond_a["name"]},
        },
    )
    assert ok_pond.status_code == 200, ok_pond.text
    assert ok_pond.json()["result"]["pond"]["id"] == pond_a["id"]

    other = client.post(
        "/mcp",
        headers=mcp,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "get_pond",
            "params": {"name": pond_b["name"]},
        },
    )
    assert other.status_code in {200, 404}
    if other.status_code == 200:
        err = other.json().get("error") or other.json().get("result", {})
        code = err.get("code") if isinstance(err, dict) else None
        result = other.json().get("result") or {}
        assert code in {"pond_not_found", "forbidden", None} or result.get("status") == "error" or (
            isinstance(result, dict) and result.get("code") in {"pond_not_found", "forbidden"}
        )
        if "pond" in result:
            assert result["pond"]["id"] != pond_b["id"]


def test_wrong_password_returns_401() -> None:
    """Wrong password while issued/active → 401."""
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _create_temp_access(headers, pond["id"])
    assert created["response"].status_code == 201, created["response"].text
    slug = created["body"]["slug"]

    denied = client.get("/mcp", headers=_basic(slug, "not-the-password"))
    assert denied.status_code == 401
    assert denied.json().get("code") == "agent_bad_credentials"


def test_forbidden_lifecycle_tools_fail_for_temp_actor() -> None:
    """Active → create/delete denied for temp-access actor."""
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _create_temp_access(headers, pond["id"])
    assert created["response"].status_code == 201, created["response"].text
    mcp = _basic(created["body"]["slug"], created["body"]["password"])

    for method, params in (
        ("create_pond", {"name": _unique("nope")}),
        ("delete_pond", {"name": pond["name"]}),
        ("stop_pond", {"name": pond["name"]}),
        ("start_pond", {"name": pond["name"]}),
    ):
        response = client.post(
            "/mcp",
            headers=mcp,
            json={"jsonrpc": "2.0", "id": method, "method": method, "params": params},
        )
        assert response.status_code in {200, 401, 403, 404}, response.text
        body = response.json()
        if response.status_code == 200:
            result = body.get("result") or {}
            error = body.get("error")
            assert error is not None or result.get("status") in {
                "error",
                "forbidden",
            } or result.get("code") in {
                "forbidden",
                "agent_disabled",
                "pond_not_found",
            }, body


def test_run_sql_via_temp_access_uses_console_path() -> None:
    """SQL for temp actors goes through the same console execution path as the web console.

    Asserts the MCP run_sql call is accepted for the pinned pond. Non-superuser
    `koi_console` behavior depends on PR #198 and is asserted there / after merge.
    """
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _create_temp_access(headers, pond["id"])
    assert created["response"].status_code == 201, created["response"].text
    mcp = _basic(created["body"]["slug"], created["body"]["password"])

    response = client.post(
        "/mcp",
        headers=mcp,
        json={
            "jsonrpc": "2.0",
            "id": 9,
            "method": "run_sql",
            "params": {
                "pond_name": pond["name"],
                "query": "SELECT 1 AS n",
                "mode": "read",
            },
        },
    )
    # Until the pond DB is reachable this may be sql_error; it must not be auth/scope denial.
    assert response.status_code == 200, response.text
    result = response.json().get("result") or {}
    assert result.get("code") not in {
        "agent_bad_credentials",
        "forbidden",
        "agent_disabled",
    }, result


def test_create_temp_access_for_foreign_pond_returns_404() -> None:
    """Owner boundary: cannot issue a token for a pond that is not yours."""
    reset_pond_tables()
    headers = auth_headers()
    missing = str(uuid.uuid4())
    response = client.post(
        f"/api/v1/ponds/{missing}/temp-access",
        headers=headers,
        json={
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "scopes": ["whoami", "get_pond", "run_sql"],
        },
    )
    assert response.status_code == 404
    assert response.json().get("code") == "pond_not_found"


def test_revoke_unknown_token_returns_404() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    response = client.post(
        f"/api/v1/ponds/{pond['id']}/temp-access/{uuid.uuid4()}/revoke",
        headers=headers,
    )
    assert response.status_code == 404


def test_create_temp_access_invalid_scope_returns_validation_422_no_side_effects() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    before = _count_pond_tokens(pond["id"])

    created = _post_temp_access(headers, pond["id"], scopes=["not_a_real_tool"])
    _assert_scopes_validation_422(created["response"])
    assert _count_pond_tokens(pond["id"]) == before


def test_create_temp_access_empty_scope_string_returns_422_no_side_effects() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    before = _count_pond_tokens(pond["id"])

    created = _post_temp_access(headers, pond["id"], scopes=[""])
    _assert_scopes_validation_422(created["response"])
    assert _count_pond_tokens(pond["id"]) == before


def test_create_temp_access_disallowed_scope_returns_422_no_side_effects() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    before = _count_pond_tokens(pond["id"])

    created = _post_temp_access(headers, pond["id"], scopes=["confirm_action"])
    _assert_scopes_validation_422(created["response"])
    assert _count_pond_tokens(pond["id"]) == before


def test_create_temp_access_mixed_scopes_rejects_whole_request_422() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    before = _count_pond_tokens(pond["id"])

    created = _post_temp_access(headers, pond["id"], scopes=["whoami", "delete_pond"])
    _assert_scopes_validation_422(created["response"])
    assert _count_pond_tokens(pond["id"]) == before


def test_create_temp_access_empty_list_null_and_omitted_keep_default_scopes() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)

    cases = (
        _post_temp_access(headers, pond["id"], scopes=[]),
        _post_temp_access(headers, pond["id"], scopes=None),
        _post_temp_access(headers, pond["id"], include_scopes=False),
    )
    for created in cases:
        assert created["response"].status_code == 201, created["response"].text
        body = created["body"]
        assert set(body["scopes"]) == DEFAULT_TEMP_SCOPES, body
        assert body.get("password")
        assert body.get("slug") or body.get("url")


def test_create_temp_access_valid_subset_and_duplicates_preserve_scope_contract() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)

    subset = ["whoami", "get_pond"]
    created = _post_temp_access(headers, pond["id"], scopes=subset)
    assert created["response"].status_code == 201, created["response"].text
    assert created["body"]["scopes"] == subset, created["body"]

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        stored = connection.execute(
            text("SELECT scopes FROM pond_tokens WHERE id = :id"),
            {"id": created["body"]["id"]},
        ).scalar_one()
    engine.dispose()
    assert list(stored) == subset

    dupes = ["whoami", "whoami"]
    duplicated = _post_temp_access(headers, pond["id"], scopes=dupes)
    assert duplicated["response"].status_code == 201, duplicated["response"].text
    assert duplicated["body"]["scopes"] == dupes, duplicated["body"]

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        stored_dupes = connection.execute(
            text("SELECT scopes FROM pond_tokens WHERE id = :id"),
            {"id": duplicated["body"]["id"]},
        ).scalar_one()
    engine.dispose()
    assert list(stored_dupes) == dupes


def test_create_temp_access_wrong_scopes_type_retains_validation_422() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    before = _count_pond_tokens(pond["id"])

    as_string = _post_temp_access(headers, pond["id"], scopes="whoami")
    _assert_scopes_validation_422(as_string["response"], require_value_error=False)
    assert _count_pond_tokens(pond["id"]) == before

    as_number = _post_temp_access(headers, pond["id"], scopes=42)
    _assert_scopes_validation_422(as_number["response"], require_value_error=False)
    assert _count_pond_tokens(pond["id"]) == before


def test_create_temp_access_auth_and_ownership_failures_unchanged() -> None:
    reset_pond_tables()
    missing = str(uuid.uuid4())
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    valid_body = {
        "expires_at": expires_at,
        "scopes": ["whoami", "get_pond", "run_sql"],
    }

    unauth = client.post(f"/api/v1/ponds/{missing}/temp-access", json=valid_body)
    assert unauth.status_code == 401, unauth.text

    headers = auth_headers()
    foreign = client.post(
        f"/api/v1/ponds/{missing}/temp-access",
        headers=headers,
        json=valid_body,
    )
    assert foreign.status_code == 404, foreign.text
    assert foreign.json().get("code") == "pond_not_found"


def test_mcp_forbidden_scope_remains_agent_disabled_403() -> None:
    reset_pond_tables()
    headers = auth_headers()
    pond = _create_running_pond(headers)
    created = _post_temp_access(headers, pond["id"], scopes=["whoami", "get_pond"])
    assert created["response"].status_code == 201, created["response"].text
    mcp = _basic(created["body"]["slug"], created["body"]["password"])

    response = client.post(
        "/mcp",
        headers=mcp,
        json={
            "jsonrpc": "2.0",
            "id": 42,
            "method": "run_sql",
            "params": {
                "pond_name": pond["name"],
                "query": "SELECT 1 AS n",
                "mode": "read",
            },
        },
    )
    body = response.json()
    if response.status_code in {401, 403}:
        assert body.get("code") == "agent_disabled", body
    else:
        assert response.status_code == 200, response.text
        result = body.get("result") or {}
        error = body.get("error") or {}
        code = (
            body.get("code")
            or result.get("code")
            or (error.get("code") if isinstance(error, dict) else None)
        )
        assert code == "agent_disabled" or (
            isinstance(result, dict) and result.get("status") == "error"
            and "agent_disabled" in str(result)
        ), body
