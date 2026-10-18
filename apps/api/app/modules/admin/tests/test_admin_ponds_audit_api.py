from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, UserRole
from app.core.models import User
from app.main import app
from app.modules.admin import AdminService
from app.modules.auth import AuthService
from tests.db_reset import reset_auth_tables

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


async def test_admin_list_ponds_returns_owner_and_state() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-ponds@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-ponds@koicloud.dev")

        response = await client.get(
            "/api/v1/admin/ponds",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert len(body["ponds"]) >= 1
    for pond in body["ponds"]:
        assert "owner_email" in pond
        assert "desired_state" in pond
        assert "observed_state" in pond

    listed = await AdminService.list_ponds()
    assert listed.next_cursor is None
    assert len(listed.ponds) == len(body["ponds"])


async def test_admin_list_audit_returns_actor_action_target() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-audit@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-audit@koicloud.dev")

        response = await client.get(
            "/api/v1/admin/audit",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert len(body["events"]) >= 1
    for event in body["events"]:
        assert "actor_kind" in event
        assert "action" in event
        assert "target_kind" in event
        assert "target_id" in event
        assert "at" in event
        assert "metadata" in event
        assert event["action"] in SENSITIVE_AUDIT_ACTIONS

    listed = await AdminService.list_audit()
    assert listed.next_cursor is None
    assert len(listed.events) == len(body["events"])


async def test_non_admin_cannot_list_ponds_or_audit() -> None:
    reset_auth_tables()

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
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-readonly@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-readonly@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}

        ponds_post = await client.post("/api/v1/admin/ponds", headers=headers, json={})
        audit_post = await client.post("/api/v1/admin/audit", headers=headers, json={})

    assert ponds_post.status_code == 405
    assert audit_post.status_code == 405
