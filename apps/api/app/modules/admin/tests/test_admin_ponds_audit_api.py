from __future__ import annotations

from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, UserRole
from app.core.models import User
from app.core.time import utc_now
from app.main import app
from app.modules.admin import AdminService
from app.modules.auth import AuthService
from tests.db_reset import reset_pond_tables

PASSWORD = "Sup3rSegura!2026"

SENSITIVE_AUDIT_ACTIONS = {
    "suspend_user",
    "reveal_agent_access",
    "delete_pond",
    "restore_backup",
}


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_and_verify(client: AsyncClient, email: str) -> UUID:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Admin Fixture"},
    )
    assert registered.status_code == 201
    user_id = UUID(registered.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    verified = await client.post("/api/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200
    return user_id


async def _login(client: AsyncClient, email: str) -> str:
    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["access_token"]


async def _promote(user_id: UUID, role: UserRole) -> None:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.role = role
        await session.commit()


async def _clear_audit_events() -> None:
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM audit_events"))
        await session.commit()


async def _seed_audit_event(
    *,
    actor_user_id: UUID,
    action: str,
    target_id: UUID,
    target_kind: str = "pond",
) -> UUID:
    event_id = uuid4()
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO audit_events (
                    id, actor_user_id, actor_kind, target_kind, target_id, action, metadata, at
                )
                VALUES (
                    :id, :actor_user_id, 'admin', :target_kind, :target_id, :action,
                    CAST(:metadata AS jsonb), :at
                )
                """
            ),
            {
                "id": str(event_id),
                "actor_user_id": str(actor_user_id),
                "target_kind": target_kind,
                "target_id": str(target_id),
                "action": action,
                "metadata": '{"source": "test"}',
                "at": utc_now(),
            },
        )
        await session.commit()
    return event_id


async def _create_running_pond(client: AsyncClient, token: str, name: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/v1/ponds", headers=headers, json={"name": name})
    assert created.status_code == 202
    body = created.json()
    pond = body["pond"]
    job_id = body["job"]["id"]

    claimed = await client.post(
        "/internal/v1/jobs/claim",
        headers={"X-Node-Token": get_settings().node_token},
        json={},
    )
    assert claimed.status_code == 200

    done = await client.post(
        f"/internal/v1/jobs/{job_id}/complete",
        headers={"X-Node-Token": get_settings().node_token},
        json={"status": "succeeded", "result": {"observed_state": "running"}},
    )
    assert done.status_code == 204
    return pond


async def test_admin_list_ponds_returns_seeded_owner_and_state() -> None:
    reset_pond_tables()
    await _clear_audit_events()

    async with _make_client() as client:
        await _register_and_verify(client, "owner-ponds@koicloud.dev")
        owner_token = await _login(client, "owner-ponds@koicloud.dev")
        pond = await _create_running_pond(client, owner_token, "admin-list-demo")

        admin_id = await _register_and_verify(client, "admin-ponds@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        admin_token = await _login(client, "admin-ponds@koicloud.dev")

        response = await client.get(
            "/api/v1/admin/ponds",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    match = next(row for row in body["ponds"] if row["id"] == pond["id"])
    assert match["owner_email"] == "owner-ponds@koicloud.dev"
    assert match["name"] == "admin-list-demo"
    assert match["desired_state"] == "running"
    assert match["observed_state"] == "running"
    assert match["plan_id"] == pond["plan_id"]
    assert match["node_id"] == pond["node_id"]
    assert match["host_port"] == pond["host_port"]

    listed = await AdminService.list_ponds()
    assert any(row.id == UUID(pond["id"]) for row in listed.ponds)


async def test_admin_list_audit_returns_seeded_sensitive_event() -> None:
    reset_pond_tables()
    await _clear_audit_events()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-audit@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        admin_token = await _login(client, "admin-audit@koicloud.dev")
        target_id = uuid4()
        event_id = await _seed_audit_event(
            actor_user_id=admin_id,
            action="delete_pond",
            target_id=target_id,
        )

        response = await client.get(
            "/api/v1/admin/audit",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    match = next(row for row in body["events"] if row["id"] == str(event_id))
    assert match["actor_user_id"] == str(admin_id)
    assert match["actor_kind"] == "admin"
    assert match["action"] == "delete_pond"
    assert match["target_kind"] == "pond"
    assert match["target_id"] == str(target_id)
    assert match["metadata"] == {"source": "test"}
    assert "at" in match
    assert match["action"] in SENSITIVE_AUDIT_ACTIONS

    listed = await AdminService.list_audit()
    assert any(row.id == event_id for row in listed.events)


async def test_admin_list_audit_excludes_non_sensitive_actions() -> None:
    reset_pond_tables()
    await _clear_audit_events()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-audit-filter@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        admin_token = await _login(client, "admin-audit-filter@koicloud.dev")
        sensitive_id = await _seed_audit_event(
            actor_user_id=admin_id,
            action="delete_pond",
            target_id=uuid4(),
        )
        non_sensitive_id = await _seed_audit_event(
            actor_user_id=admin_id,
            action="login",
            target_id=uuid4(),
            target_kind="user",
        )

        response = await client.get(
            "/api/v1/admin/audit",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert response.status_code == 200
    events = response.json()["events"]
    ids = {row["id"] for row in events}
    assert str(sensitive_id) in ids
    assert str(non_sensitive_id) not in ids
    assert all(row["action"] in SENSITIVE_AUDIT_ACTIONS for row in events)


async def test_non_admin_cannot_list_ponds_or_audit() -> None:
    reset_pond_tables()
    await _clear_audit_events()

    async with _make_client() as client:
        await _register_and_verify(client, "client-ponds-audit@koicloud.dev")
        token = await _login(client, "client-ponds-audit@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}

        ponds = await client.get("/api/v1/admin/ponds", headers=headers)
        audit = await client.get("/api/v1/admin/audit", headers=headers)

    assert ponds.status_code == 403
    assert ponds.json()["code"] == "admin_only"
    assert audit.status_code == 403
    assert audit.json()["code"] == "admin_only"


async def test_admin_ponds_and_audit_are_read_only_get() -> None:
    reset_pond_tables()
    await _clear_audit_events()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-readonly@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-readonly@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}

        ponds_post = await client.post("/api/v1/admin/ponds", headers=headers, json={})
        audit_post = await client.post("/api/v1/admin/audit", headers=headers, json={})

    assert ponds_post.status_code == 405
    assert audit_post.status_code == 405


async def test_admin_list_ponds_empty_without_rows() -> None:
    reset_pond_tables()
    await _clear_audit_events()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-empty-ponds@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-empty-ponds@koicloud.dev")

        response = await client.get(
            "/api/v1/admin/ponds",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["ponds"] == []
    assert response.json()["next_cursor"] is None
