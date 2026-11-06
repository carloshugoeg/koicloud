"""Verify-email delivery on register and neutral resend-verification.

Phase 1 (red): these assert the target contract before production wiring.
Never log or assert plaintext tokens, Resend API keys, or secrets.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind
from app.core.models import EmailToken, User
from app.main import app
from app.modules.notifications.service import bootstrap_email_gate, reset_email_gate_for_tests
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _email_gate_isolation(monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    reset_email_gate_for_tests()
    monkeypatch.setenv("ENVIRONMENT", "development")
    yield
    get_settings.cache_clear()
    reset_email_gate_for_tests()


def _set_provider(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER", provider)
    if provider == "resend":
        monkeypatch.setenv("RESEND_API_KEY", "re_test_placeholder_not_a_real_key")
        monkeypatch.setenv("EMAIL_FROM", "noreply@koicloud.dev")
    get_settings.cache_clear()
    bootstrap_email_gate(get_settings())


def _register_payload(email: str) -> dict[str, str]:
    return {
        "email": email,
        "password": PASSWORD,
        "full_name": "Verify Send User",
    }


async def test_register_with_resend_calls_send_verify_email_and_does_not_log_token(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reset_auth_tables()
    _set_provider(monkeypatch, "resend")

    sent: list[tuple[str, str, dict[str, Any]]] = []

    def fake_send(template: str, to: str, context: dict[str, Any]) -> MagicMock:
        sent.append((template, to, context))
        return MagicMock(template=template, to=to)

    monkeypatch.setattr("app.modules.notifications.send", fake_send)
    monkeypatch.setattr("app.commands.auth.send", fake_send, raising=False)

    email = "resend_register@koicloud.dev"
    with caplog.at_level(logging.INFO):
        async with _make_client() as client:
            response = await client.post("/api/v1/auth/register", json=_register_payload(email))

    assert response.status_code == 201
    assert len(sent) == 1
    template, to, context = sent[0]
    assert template == "verify_email"
    assert to == email
    assert context["email"] == email
    assert "url" in context
    assert "token=" in str(context["url"])

    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "verify_email token" not in joined
    # Plaintext must not appear in logs; the URL query is only in the send context.
    token_part = str(context["url"]).split("token=", 1)[-1]
    assert token_part
    assert token_part not in joined


async def test_register_with_console_may_log_token_and_skips_live_resend_path(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reset_auth_tables()
    _set_provider(monkeypatch, "console")

    live_resend_posts: list[object] = []

    def refuse_live_post(*_args: object, **_kwargs: object) -> None:
        live_resend_posts.append((_args, _kwargs))
        raise AssertionError("console provider must not hit the live Resend HTTP path")

    monkeypatch.setattr(
        "app.modules.notifications.resend.default_post",
        refuse_live_post,
        raising=False,
    )
    monkeypatch.setattr(
        "app.modules.notifications.resend.deliver_via_resend",
        refuse_live_post,
        raising=False,
    )

    send_calls: list[tuple[str, str, dict[str, Any]]] = []

    def tracking_send(template: str, to: str, context: dict[str, Any]) -> MagicMock:
        send_calls.append((template, to, context))
        return MagicMock(template=template, to=to)

    # Console path may call send (console printer) or only log; either is fine
    # as long as the live Resend path stays cold.
    monkeypatch.setattr("app.modules.notifications.send", tracking_send, raising=False)
    monkeypatch.setattr("app.commands.auth.send", tracking_send, raising=False)

    email = "console_register@koicloud.dev"
    with caplog.at_level(logging.INFO, logger="app.commands.auth"):
        async with _make_client() as client:
            response = await client.post("/api/v1/auth/register", json=_register_payload(email))

    assert response.status_code == 201
    assert live_resend_posts == []

    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one()
        tokens = (
            await session.execute(
                select(EmailToken).where(
                    EmailToken.user_id == user.id,
                    EmailToken.kind == EmailTokenKind.VERIFY_EMAIL,
                )
            )
        ).scalars().all()
        assert len(tokens) == 1

    joined = "\n".join(record.getMessage() for record in caplog.records)
    # Console may log the plaintext verify token (existing pack R-03 behavior).
    assert ("verify_email token for" in joined) or send_calls


async def test_resend_verification_is_202_for_unknown_and_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_auth_tables()
    _set_provider(monkeypatch, "resend")

    sent: list[tuple[str, str, dict[str, Any]]] = []

    def fake_send(template: str, to: str, context: dict[str, Any]) -> MagicMock:
        sent.append((template, to, context))
        return MagicMock(template=template, to=to)

    monkeypatch.setattr("app.modules.notifications.send", fake_send)
    monkeypatch.setattr("app.commands.auth.send", fake_send, raising=False)

    async with _make_client() as client:
        unknown = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "ghost_resend@koicloud.dev"},
        )
        assert unknown.status_code == 202
        assert unknown.json() == {"ok": True}
        assert sent == []

        create = await client.post(
            "/api/v1/auth/register",
            json=_register_payload("unverified_resend@koicloud.dev"),
        )
        assert create.status_code == 201
        sent.clear()

        again = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "unverified_resend@koicloud.dev"},
        )
        assert again.status_code == 202
        assert again.json() == {"ok": True}
        assert len(sent) == 1
        assert sent[0][0] == "verify_email"
        assert sent[0][1] == "unverified_resend@koicloud.dev"


async def test_reregister_unverified_resends_and_verified_stays_email_taken(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_auth_tables()
    _set_provider(monkeypatch, "resend")

    sent: list[tuple[str, str, dict[str, Any]]] = []

    def fake_send(template: str, to: str, context: dict[str, Any]) -> MagicMock:
        sent.append((template, to, context))
        return MagicMock(template=template, to=to)

    monkeypatch.setattr("app.modules.notifications.send", fake_send)
    monkeypatch.setattr("app.commands.auth.send", fake_send, raising=False)

    email = "reregister@koicloud.dev"
    async with _make_client() as client:
        first = await client.post("/api/v1/auth/register", json=_register_payload(email))
        assert first.status_code == 201
        user_id = UUID(first.json()["user_id"])
        assert len(sent) >= 1
        sent.clear()

        second = await client.post("/api/v1/auth/register", json=_register_payload(email))
        assert second.status_code == 201
        assert UUID(second.json()["user_id"]) == user_id
        assert second.json()["email_verified"] is False
        assert len(sent) == 1
        assert sent[0][0] == "verify_email"

        from app.modules.auth import AuthService

        token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
        verified = await client.post("/api/v1/auth/verify", json={"token": token})
        assert verified.status_code == 200

        taken = await client.post("/api/v1/auth/register", json=_register_payload(email))
        assert taken.status_code == 409
        assert taken.json()["code"] == "email_taken"
