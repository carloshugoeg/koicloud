"""Forgot-password delivery and email logo contract (Phase 1 red).

Never log or assert plaintext tokens, Resend API keys, or secrets.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind
from app.core.models import EmailToken
from app.main import app
from app.modules.auth import AuthService
from app.modules.notifications.errors import NotificationDeliveryError
from app.modules.notifications.service import (
    NotificationResult,
    bootstrap_email_gate,
    reset_email_gate_for_tests,
)
from app.modules.notifications.templates import render_template
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"
HTTPS_PNG_LOGO = re.compile(
    r'src="(https://[^"]+/koi/koi-mark-32\.png)"',
    re.IGNORECASE,
)


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _email_gate_isolation(monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    reset_email_gate_for_tests()
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    get_settings.cache_clear()
    bootstrap_email_gate(get_settings())
    yield
    get_settings.cache_clear()
    reset_email_gate_for_tests()


async def _register_and_verify(client: AsyncClient, email: str) -> UUID:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Forgot Reset User"},
    )
    assert response.status_code == 201
    user_id = UUID(response.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    verified = await client.post("/api/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200
    return user_id


def _capture_send(monkeypatch: pytest.MonkeyPatch) -> list[NotificationResult]:
    sent: list[NotificationResult] = []

    def fake_send(template: str, to: str, context: dict[str, Any]) -> NotificationResult:
        rendered = render_template(template, context)
        result = NotificationResult(
            template=rendered.template,
            to=to,
            subject=rendered.subject,
            text_body=rendered.text_body,
            html_body=rendered.html_body,
        )
        sent.append(result)
        return result

    monkeypatch.setattr("app.modules.notifications.send", fake_send)
    monkeypatch.setattr("app.commands.auth.send", fake_send, raising=False)
    return sent


async def test_forgot_known_email_sends_one_reset_email_with_token_link_and_png_logo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_auth_tables()
    sent = _capture_send(monkeypatch)
    email = "forgot_known@koicloud.dev"

    async with _make_client() as client:
        await _register_and_verify(client, email)
        sent.clear()
        response = await client.post("/api/v1/auth/forgot", json={"email": email})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(sent) == 1
    mail = sent[0]
    assert mail.template == "reset_password"
    assert mail.to == email
    assert "/reset?token=" in mail.text_body
    assert "/reset?token=" in mail.html_body
    match = HTTPS_PNG_LOGO.search(mail.html_body)
    assert match is not None
    assert match.group(1).startswith("https://")
    assert match.group(1).endswith(".png")
    assert "app.koicloud.dev" not in match.group(1)


async def test_forgot_unknown_email_same_response_sends_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_auth_tables()
    sent = _capture_send(monkeypatch)
    known = "forgot_parity@koicloud.dev"
    unknown = "ghost_forgot@koicloud.dev"

    async with _make_client() as client:
        await _register_and_verify(client, known)
        sent.clear()
        known_res = await client.post("/api/v1/auth/forgot", json={"email": known})
        known_body = known_res.json()
        known_status = known_res.status_code
        sent_after_known = list(sent)
        sent.clear()

        unknown_res = await client.post("/api/v1/auth/forgot", json={"email": unknown})

    assert unknown_res.status_code == known_status == 200
    assert unknown_res.json() == known_body == {"ok": True}
    assert len(sent_after_known) == 1
    assert sent == []


async def test_verify_email_logo_is_absolute_https_png() -> None:
    rendered = render_template(
        "verify_email",
        {
            "url": "https://koicloud-web.vercel.app/verify?token=sample-not-real",
            "email": "logo_check@koicloud.dev",
        },
    )
    match = HTTPS_PNG_LOGO.search(rendered.html_body)
    assert match is not None
    logo_url = match.group(1)
    assert logo_url.startswith("https://")
    assert logo_url.endswith(".png")
    assert "app.koicloud.dev" not in logo_url


async def test_forgot_returns_ok_when_reset_email_delivery_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_auth_tables()
    email = "forgot_delivery_fail@koicloud.dev"

    def failing_send(template: str, to: str, context: dict[str, Any]) -> NotificationResult:
        raise NotificationDeliveryError(
            f"Resend delivery failed template={template} to={to}"
        )

    monkeypatch.setattr("app.modules.notifications.send", failing_send)
    monkeypatch.setattr("app.commands.auth.send", failing_send, raising=False)

    async with _make_client() as client:
        user_id = await _register_and_verify(client, email)
        response = await client.post("/api/v1/auth/forgot", json={"email": email})

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    async with SessionLocal() as session:
        reset_tokens = (
            await session.execute(
                select(EmailToken).where(
                    EmailToken.user_id == user_id,
                    EmailToken.kind == EmailTokenKind.RESET_PASSWORD,
                    EmailToken.consumed_at.is_(None),
                )
            )
        ).scalars().all()
        assert len(reset_tokens) >= 1
