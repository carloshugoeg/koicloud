from __future__ import annotations

from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from app.core.enums import EmailTokenKind
from app.main import app
from app.modules.auth import AuthService
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_active_user(
    client: AsyncClient,
    email: str = "subscriber@koicloud.dev",
    full_name: str = "Subscriber User",
) -> tuple[UUID, str]:
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name},
    )
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
    return user_id, login_res.json()["access_token"]


async def test_subscribe_micro_happy_path() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id, token = await _create_active_user(client, email="micro_happy@koicloud.dev")

        response = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_id": "micro"},
        )
        assert response.status_code == 202
        data = response.json()

        assert set(data.keys()) >= {"subscription", "invoice", "payment"}

        sub = data["subscription"]
        assert sub["plan_id"] == "micro"
        assert sub["user_id"] == str(user_id)
        assert sub["status"] == "active"
        assert sub["cancel_at_period_end"] is False

        invoice = data["invoice"]
        assert invoice["user_id"] == str(user_id)
        assert invoice["number"].startswith("KC-")
        assert invoice["total_usd"] == 5.0

        payment = data["payment"]
        assert payment["status"] == "succeeded"
        assert payment["method"] == "simulated"


async def test_subscribe_unauthorized() -> None:
    async with _make_client() as client:
        response = await client.post(
            "/api/v1/subscriptions",
            json={"plan_id": "micro"},
        )
        assert response.status_code == 401


async def test_subscribe_plan_required() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        _, token = await _create_active_user(client, email="empty_plan@koicloud.dev")

        response = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_id": ""},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "plan_required"


async def test_subscribe_cli_requires_confirmation() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        _, token = await _create_active_user(client, email="cli_sub@koicloud.dev")

        response = await client.post(
            "/api/v1/subscriptions",
            headers={
                "Authorization": f"Bearer {token}",
                "X-KOI-Surface": "cli",
            },
            json={"plan_id": "micro"},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["status"] == "confirmation_required"
        assert "token" in body
        assert "micro" in body["summary"]


async def test_cancel_subscription_happy_path() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        _, token = await _create_active_user(client, email="cancel_sub@koicloud.dev")

        sub_res = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_id": "micro"},
        )
        assert sub_res.status_code == 202
        sub_id = sub_res.json()["subscription"]["id"]

        cancel_res = await client.post(
            f"/api/v1/subscriptions/{sub_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_res.status_code == 202
        data = cancel_res.json()
        assert data["subscription"]["id"] == sub_id
        assert data["subscription"]["cancel_at_period_end"] is True


async def test_cancel_subscription_not_owner() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        _, token_a = await _create_active_user(client, email="owner_a@koicloud.dev")
        _, token_b = await _create_active_user(client, email="owner_b@koicloud.dev")

        sub_res = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"plan_id": "micro"},
        )
        assert sub_res.status_code == 202
        sub_id = sub_res.json()["subscription"]["id"]

        cancel_res = await client.post(
            f"/api/v1/subscriptions/{sub_id}/cancel",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert cancel_res.status_code == 403
        assert cancel_res.json()["code"] == "not_owner"


async def test_cancel_subscription_cli_requires_confirmation() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        _, token = await _create_active_user(client, email="cli_cancel@koicloud.dev")
        sub_id = uuid4()

        response = await client.post(
            f"/api/v1/subscriptions/{sub_id}/cancel",
            headers={
                "Authorization": f"Bearer {token}",
                "X-KOI-Surface": "cli",
            },
        )
        assert response.status_code == 409
        body = response.json()
        assert body["status"] == "confirmation_required"
        assert str(sub_id) in body["summary"]
