from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.core.auth import AuthContext
from app.core.db import SessionLocal
from app.core.enums import AppSurface, EmailTokenKind, UserRole, UserStatus
from app.core.models import User
from app.main import app
from app.modules.auth import AuthService
from app.modules.users import UserService
from app.schemas import UpdateProfileRequest
from tests.db_reset import reset_auth_tables, reset_pond_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(
    client: AsyncClient,
    email: str = "user_profile@koicloud.dev",
    full_name: str = "Initial Profile Name",
    nit: str | None = "0614-100199-102-4",
) -> tuple[UUID, str]:
    """Register, verify email, login, and return (user_id, access_token)."""
    register_payload = {
        "email": email,
        "password": PASSWORD,
        "full_name": full_name,
    }
    if nit is not None:
        register_payload["nit"] = nit

    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    user_id = UUID(reg_res.json()["user_id"])

    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    verify_res = await client.post("/api/v1/auth/verify", json={"token": token})
    assert verify_res.status_code == 200

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]
    return user_id, access_token


async def test_get_me_happy_path() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id, token = await _create_active_user(
            client,
            email="get_me_happy@koicloud.dev",
            full_name="Get Me User",
            nit="0614-111111-101-1",
        )

        response = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "user" in data
        assert "subscription" in data
        assert "ponds_count" in data

        user_data = data["user"]
        assert user_data["id"] == str(user_id)
        assert user_data["email"] == "get_me_happy@koicloud.dev"
        assert user_data["full_name"] == "Get Me User"
        assert user_data["nit"] == "0614-111111-101-1"
        assert user_data["email_verified"] is True
        assert data["subscription"] is None
        assert data["ponds_count"] == 0


async def test_get_me_with_subscription_and_ponds() -> None:
    reset_pond_tables()

    async with _make_client() as client:
        user_id, token = await _create_active_user(
            client,
            email="with_sub_pond@koicloud.dev",
            full_name="Sub Pond User",
        )

        # Create pond via API (PondService automatically ensures active subscription)
        create_res = await client.post(
            "/api/v1/ponds",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "user-pond-01"},
        )
        assert create_res.status_code == 202

        response = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["ponds_count"] == 1
        assert data["subscription"] is not None
        assert data["subscription"]["user_id"] == str(user_id)


async def test_patch_me_happy_path() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id, token = await _create_active_user(
            client,
            email="patch_happy@koicloud.dev",
            full_name="Old Name",
            nit="0614-000000-000-0",
        )

        response = await client.patch(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": "New Updated Name",
                "nit": "0614-220999-101-3",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["id"] == str(user_id)
        assert data["user"]["full_name"] == "New Updated Name"
        assert data["user"]["nit"] == "0614-220999-101-3"

        # Verify DB reflects the update
        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            assert user.full_name == "New Updated Name"
            assert user.nit == "0614-220999-101-3"


async def test_patch_me_partial_update() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id, token = await _create_active_user(
            client,
            email="partial_patch@koicloud.dev",
            full_name="Original Name",
            nit="0614-777777-777-7",
        )

        # Update only full_name; NIT should remain unchanged
        response = await client.patch(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"full_name": "Updated Only Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["full_name"] == "Updated Only Name"
        assert data["user"]["nit"] == "0614-777777-777-7"

        # Update only NIT; full_name should remain unchanged
        response_nit = await client.patch(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"nit": "0614-888888-888-8"},
        )
        assert response_nit.status_code == 200
        data_nit = response_nit.json()
        assert data_nit["user"]["full_name"] == "Updated Only Name"
        assert data_nit["user"]["nit"] == "0614-888888-888-8"


async def test_me_unauthorized_and_invalid_token() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        # GET without header
        get_res = await client.get("/api/v1/me")
        assert get_res.status_code == 401

        # PATCH without header
        patch_res = await client.patch(
            "/api/v1/me",
            json={"full_name": "Hacker"},
        )
        assert patch_res.status_code == 401

        # GET with invalid token
        inv_res = await client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        )
        assert inv_res.status_code == 401


async def test_user_service_direct() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id, _ = await _create_active_user(
            client,
            email="direct_service@koicloud.dev",
            full_name="Direct User",
            nit="0614-999999-999-9",
        )

    actor = AuthContext(
        user_id=str(user_id),
        email="direct_service@koicloud.dev",
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.WEB,
    )

    me_res = await UserService.get_me(actor)
    assert me_res.user.id == user_id
    assert me_res.user.full_name == "Direct User"
    assert me_res.ponds_count == 0

    patch_res = await UserService.update_profile(
        actor,
        UpdateProfileRequest(full_name="Direct Updated", nit="0614-000111-222-3"),
    )
    assert patch_res.user.full_name == "Direct Updated"
    assert patch_res.user.nit == "0614-000111-222-3"
