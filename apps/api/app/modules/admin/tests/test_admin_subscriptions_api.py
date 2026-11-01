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


async def test_admin_list_subscriptions_returns_rows_and_cursor() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        owner_id = await _register_and_verify(client, "owner-subs@koicloud.dev")
        owner_token = await _login(client, "owner-subs@koicloud.dev")
        subscribed = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"plan_id": "micro"},
        )
        assert subscribed.status_code == 202
        sub = subscribed.json()["subscription"]

        admin_id = await _register_and_verify(client, "admin-subs@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        admin_token = await _login(client, "admin-subs@koicloud.dev")

        response = await client.get(
            "/api/v1/admin/subscriptions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert "subscriptions" in body
    match = next(row for row in body["subscriptions"] if row["id"] == sub["id"])
    assert match["user_id"] == str(owner_id)
    assert match["user_email"] == "owner-subs@koicloud.dev"
    assert match["plan_id"] == "micro"
    assert match["status"] == "active"
    assert match["cancel_at_period_end"] is False
    assert "current_period_start" in match
    assert "current_period_end" in match

    listed = await AdminService.list_subscriptions()
    assert listed.next_cursor is None
    assert any(row.id == UUID(sub["id"]) for row in listed.subscriptions)


async def test_non_admin_subscriptions_receives_admin_only() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        await _register_and_verify(client, "client-subs@koicloud.dev")
        token = await _login(client, "client-subs@koicloud.dev")
        response = await client.get(
            "/api/v1/admin/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "admin_only"
