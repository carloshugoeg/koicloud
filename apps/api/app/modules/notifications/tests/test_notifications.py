from __future__ import annotations

import pytest

from app.modules.notifications import send


def test_verify_email_happy_path(capsys: pytest.CaptureFixture[str]) -> None:
    url = "https://koicloud.dev/verify?token=verify_token_abc123"
    email = "usuario@koicloud.dev"

    result = send(
        "verify_email",
        email,
        {"url": url, "email": email},
    )

    assert result.template == "verify_email"
    assert result.to == email
    assert result.subject == "Verificá tu correo"
    assert url in result.text_body
    assert url in result.html_body
    assert email in result.text_body
    assert email in result.html_body
    assert "<!DOCTYPE html>" in result.html_body

    captured = capsys.readouterr()
    assert url in captured.out
    assert email in captured.out
    assert "Verificá tu correo" in captured.out


def test_reset_password_happy_path(capsys: pytest.CaptureFixture[str]) -> None:
    url = "https://koicloud.dev/reset?token=reset_token_xyz789"
    email = "recuperar@koicloud.dev"

    result = send(
        "reset_password",
        email,
        {"url": url, "email": email},
    )

    assert result.template == "reset_password"
    assert result.to == email
    assert result.subject == "Restablecé tu contraseña"
    assert url in result.text_body
    assert url in result.html_body
    assert email in result.text_body
    assert email in result.html_body
    assert "<!DOCTYPE html>" in result.html_body

    captured = capsys.readouterr()
    assert url in captured.out
    assert email in captured.out
    assert "Restablecé tu contraseña" in captured.out


def test_invoice_issued_happy_path(capsys: pytest.CaptureFixture[str]) -> None:
    code = "FAC-2026-0042"
    total = "$25.00 USD"
    to = "cliente@koicloud.dev"

    result = send(
        "invoice_issued",
        to,
        {"code": code, "total": total},
    )

    assert result.template == "invoice_issued"
    assert result.to == to
    assert result.subject == "Tu factura de KoiCloud"
    assert code in result.text_body
    assert total in result.text_body
    assert code in result.html_body
    assert total in result.html_body

    captured = capsys.readouterr()
    assert code in captured.out
    assert total in captured.out
    assert "Tu factura de KoiCloud" in captured.out


def test_subscription_canceled_happy_path(capsys: pytest.CaptureFixture[str]) -> None:
    plan = "Carpita"
    ends_on = "2026-11-15T00:00:00Z"
    to = "suscriptor@koicloud.dev"

    result = send(
        "subscription_canceled",
        to,
        {"plan": plan, "ends_on": ends_on},
    )

    assert result.template == "subscription_canceled"
    assert result.to == to
    assert result.subject == "Cancelación programada"
    assert plan in result.text_body
    assert ends_on in result.text_body
    assert plan in result.html_body
    assert ends_on in result.html_body

    captured = capsys.readouterr()
    assert plan in captured.out
    assert ends_on in captured.out
    assert "Cancelación programada" in captured.out


def test_send_unknown_template_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown template 'non_existent_template'"):
        send("non_existent_template", "user@koicloud.dev", {"key": "val"})


@pytest.mark.parametrize(
    ("template", "context"),
    [
        ("verify_email", {"url": "https://koicloud.dev/verify"}),  # missing email
        ("verify_email", {"email": "user@koicloud.dev"}),  # missing url
        ("reset_password", {"url": "https://koicloud.dev/reset"}),  # missing email
        ("reset_password", {"email": "user@koicloud.dev"}),  # missing url
        ("invoice_issued", {"code": "FAC-1"}),  # missing total
        ("invoice_issued", {"total": "$10"}),  # missing code
        ("subscription_canceled", {"plan": "Carpita"}),  # missing ends_on
        ("subscription_canceled", {"ends_on": "2026-11-01"}),  # missing plan
    ],
)
def test_send_incomplete_context_rejected(template: str, context: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="Missing required context keys"):
        send(template, "user@koicloud.dev", context)


def test_send_empty_recipient_rejected() -> None:
    with pytest.raises(ValueError, match="Recipient 'to' must be a non-empty"):
        send("verify_email", "   ", {"url": "https://test.dev", "email": "a@b.com"})


async def test_async_await_send_support() -> None:
    url = "https://koicloud.dev/verify?token=async_test"
    email = "async@koicloud.dev"

    # Must be awaitable seamlessly for async callers
    result = await send(
        "verify_email",
        email,
        {"url": url, "email": email},
    )

    assert result.subject == "Verificá tu correo"
    assert result.to == email
