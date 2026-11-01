from __future__ import annotations

from sqlalchemy import text

from app.core.db import SessionLocal
from app.modules.billing.tests.test_subscriptions_api import _create_active_user, _make_client
from tests.db_reset import reset_auth_tables

VALID_NIT = "1000002-K"
NIT_ERROR = "El NIT no es válido. Usá los dígitos y el dígito verificador, o CF."
DECLINE_ERROR = "El pago simulado fue rechazado. Revisá la tarjeta."
PAN = "4242424242424242"
VALID_CARD = {"number": PAN, "expiry": "12/30", "cvc": "123"}


async def _active_plan(email: str) -> tuple[int, str | None, str]:
    async with SessionLocal() as session:
        count = await session.scalar(
            text(
                "SELECT COUNT(*) FROM subscriptions s "
                "JOIN users u ON u.id = s.user_id "
                "WHERE u.email = :email AND s.status = 'active'"
            ),
            {"email": email},
        )
        plan_id = await session.scalar(
            text(
                "SELECT s.plan_id FROM subscriptions s "
                "JOIN users u ON u.id = s.user_id "
                "WHERE u.email = :email AND s.status = 'active' "
                "ORDER BY s.current_period_start DESC LIMIT 1"
            ),
            {"email": email},
        )
        stored = await session.scalar(
            text(
                "SELECT COALESCE(string_agg(method || ' ' || provider || ' ' || provider_ref, ' '), '') "
                "FROM payments"
            )
        )
    return int(count or 0), None if plan_id is None else str(plan_id), str(stored or "")


async def test_invalid_nit_is_rejected_in_spanish() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, email="nit_invalid@koicloud.dev")
        response = await client.post(
            "/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_id": "micro", "nit": "0614-220999-101-3", "card": VALID_CARD},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "nit_invalid"
        assert body["message"] == NIT_ERROR


async def test_nit_accepts_check_digit_k_hyphen_spaces_and_cf() -> None:
    reset_auth_tables()
    async with _make_client() as client:
        _, token = await _create_active_user(client, email="nit_forms@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}
        spaced = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={"plan_id": "micro", "nit": " 1000002 - K "},
        )
        assert spaced.status_code == 202
        assert spaced.json()["invoice"]["nit"] == "1000002 - K"

        cf = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={"plan_id": "pro", "nit": " cf ", "card": VALID_CARD},
        )
        assert cf.status_code == 202
        assert cf.json()["invoice"]["nit"] == "CF"


async def test_plan_change_with_a_valid_card_keeps_one_active_plan() -> None:
    reset_auth_tables()
    email = "change_plan@koicloud.dev"
    async with _make_client() as client:
        _, token = await _create_active_user(client, email=email)
        headers = {"Authorization": f"Bearer {token}"}
        first = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={"plan_id": "micro"},
        )
        assert first.status_code == 202

        changed = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={"plan_id": "pro", "nit": VALID_NIT, "card": VALID_CARD},
        )
        assert changed.status_code == 202
        assert changed.json()["subscription"]["plan_id"] == "pro"
        assert PAN not in changed.text
        assert changed.json()["payment"]["method"] != VALID_CARD["cvc"]

        me = await client.get("/api/v1/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["subscription"]["plan_id"] == "pro"
        assert me.json()["user"]["nit"] == VALID_NIT

    count, plan_id, stored = await _active_plan(email)
    assert count == 1
    assert plan_id == "pro"
    assert PAN not in stored


async def test_invalid_card_is_declined_and_the_plan_stays() -> None:
    reset_auth_tables()
    email = "decline_card@koicloud.dev"
    async with _make_client() as client:
        _, token = await _create_active_user(client, email=email)
        headers = {"Authorization": f"Bearer {token}"}
        first = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={"plan_id": "micro"},
        )
        assert first.status_code == 202

        declined = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={
                "plan_id": "pro",
                "card": {"number": "4242424242424241", "expiry": "12/30", "cvc": "123"},
            },
        )
        assert declined.status_code == 422
        assert declined.json()["code"] == "payment_declined"
        assert declined.json()["message"] == DECLINE_ERROR

        expired = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={
                "plan_id": "pro",
                "card": {"number": PAN, "expiry": "01/20", "cvc": "123"},
            },
        )
        assert expired.status_code == 422
        assert expired.json()["message"] == DECLINE_ERROR

        short_cvc = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={
                "plan_id": "pro",
                "card": {"number": PAN, "expiry": "12/30", "cvc": "12"},
            },
        )
        assert short_cvc.status_code == 422

        amex = await client.post(
            "/api/v1/subscriptions",
            headers=headers,
            json={
                "plan_id": "pro",
                "card": {"number": "378282246310005", "expiry": "12/30", "cvc": "123"},
            },
        )
        assert amex.status_code == 422
        assert amex.json()["message"] == DECLINE_ERROR

        me = await client.get("/api/v1/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["subscription"]["plan_id"] == "micro"

    count, plan_id, stored = await _active_plan(email)
    assert count == 1
    assert plan_id == "micro"
    assert "4242424242424241" not in stored
    assert "378282246310005" not in stored
