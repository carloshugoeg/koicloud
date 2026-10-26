from __future__ import annotations

from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, UserRole, UserStatus
from app.core.models import AuditEvent, User
from app.main import app
from app.modules.admin import AdminService
from app.modules.auth import AuthService
from app.schemas import SuspendUserRequest
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


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


async def test_admin_list_users_returns_plan_and_cursor() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-list@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-list@koicloud.dev")

        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert len(body["users"]) >= 1
    for user in body["users"]:
        assert "active_subscription_plan" in user
        assert user["status"] in {"active", "suspended"}

    listed = await AdminService.list_users()
    assert listed.next_cursor is None
    assert len(listed.users) == len(body["users"])


async def test_non_admin_receives_admin_only() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        await _register_and_verify(client, "client-admin@koicloud.dev")
        token = await _login(client, "client-admin@koicloud.dev")
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "admin_only"


async def test_suspend_and_reactivate_user() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-suspend@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-suspend@koicloud.dev")
        target_id = await _register_and_verify(client, "target-suspend@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}

        mismatch = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers=headers,
            json={"confirm_text": "no"},
        )
        assert mismatch.status_code == 409

        suspended = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers=headers,
            json={"confirm_text": "SUSPENDER"},
        )
        assert suspended.status_code == 200
        suspended_user = suspended.json()["user"]
        assert suspended_user["id"] == str(target_id)
        assert suspended_user["status"] == "suspended"

        reactivated = await client.post(
            f"/api/v1/admin/users/{target_id}/reactivate",
            headers=headers,
        )
        assert reactivated.status_code == 200
        assert reactivated.json()["user"]["id"] == str(target_id)
        assert reactivated.json()["user"]["status"] == "active"

    via_service = await AdminService.suspend_user(
        target_id, SuspendUserRequest(confirm_text="SUSPENDER")
    )
    assert via_service.user.status == UserStatus.SUSPENDED
    cleared = await AdminService.reactivate_user(target_id)
    assert cleared.user.status == UserStatus.ACTIVE


async def test_suspend_user_stores_trimmed_reason_in_audit_metadata() -> None:
    reset_auth_tables()
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM audit_events"))
        await session.commit()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-reason@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-reason@koicloud.dev")
        target_id = await _register_and_verify(client, "target-reason@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": "  abuso de recursos  "},
        )
        assert response.status_code == 200
        assert response.json()["user"]["status"] == "suspended"

        audit = await client.get(
            "/api/v1/admin/audit",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert audit.status_code == 200
        match = next(
            event
            for event in audit.json()["events"]
            if event["action"] == "suspend_user" and event["target_id"] == str(target_id)
        )
        assert match["metadata"]["reason"] == "abuso de recursos"
        assert match["actor_user_id"] == str(admin_id)
        assert match["actor_kind"] == "admin"

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "suspend_user",
                    AuditEvent.target_id == target_id,
                )
            )
        ).scalar_one()
        assert row.event_metadata == {"reason": "abuso de recursos"}


async def test_suspend_user_omits_reason_from_metadata_when_absent() -> None:
    reset_auth_tables()
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM audit_events"))
        await session.commit()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-noreason@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-noreason@koicloud.dev")
        target_id = await _register_and_verify(client, "target-noreason@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER"},
        )
        assert response.status_code == 200

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "suspend_user",
                    AuditEvent.target_id == target_id,
                )
            )
        ).scalar_one()
        assert row.event_metadata == {}


async def test_login_rejects_suspended_account() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id = await _register_and_verify(client, "suspended-login@koicloud.dev")
        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            user.status = UserStatus.SUSPENDED
            await session.commit()

        suspended = await client.post(
            "/api/v1/auth/login",
            json={"email": "suspended-login@koicloud.dev", "password": PASSWORD},
        )

    assert suspended.status_code == 403
    assert suspended.json()["code"] == "account_suspended"


async def test_suspend_user_rejects_reason_over_500_chars() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-longreason@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-longreason@koicloud.dev")
        target_id = await _register_and_verify(client, "target-longreason@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": "x" * 501},
        )

    assert response.status_code == 422


async def test_suspend_missing_user_returns_user_not_found() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-missing@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-missing@koicloud.dev")
        missing_id = uuid4()

        response = await client.post(
            f"/api/v1/admin/users/{missing_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": "cuenta fantasma"},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "user_not_found"
