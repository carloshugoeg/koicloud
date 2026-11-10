from html import escape

from app.modules.notifications.templates import render_template

VERIFY_URL = "https://app.koicloud.dev/verify-email?token=sample-token-not-real"


def test_verify_email_has_branding_and_plain_text_fallback() -> None:
    rendered = render_template(
        "verify_email", {"url": VERIFY_URL, "email": "demo@example.invalid"}
    )
    assert rendered.subject == "Verificá tu correo"
    assert f'href="{VERIFY_URL}"' in rendered.html_body
    assert VERIFY_URL in rendered.text_body
    assert "KoiCloud" in rendered.html_body
    assert "#0A6D64" in rendered.html_body
    assert 'src="https://app.koicloud.dev/koi/koi-mark-32.png"' in rendered.html_body
    assert "KoiCloud · PaaS de datos" in rendered.html_body
    assert "24 horas" in rendered.html_body
    assert "ignorar" in rendered.html_body


def test_verify_email_escapes_user_email() -> None:
    email = "<script>alert(1)</script>@x.test"
    rendered = render_template("verify_email", {"url": VERIFY_URL, "email": email})
    assert "<script>" not in rendered.html_body
    assert escape(email, quote=True) in rendered.html_body
    assert email in rendered.text_body


def test_verify_email_escapes_url_attribute_and_display_text() -> None:
    url = VERIFY_URL + '&next="onclick="alert(1)<script>'
    rendered = render_template(
        "verify_email", {"url": url, "email": "demo@example.invalid"}
    )
    safe_url = escape(url, quote=True)
    assert f'href="{safe_url}"' in rendered.html_body
    assert f">{safe_url}</a>" in rendered.html_body
    assert url not in rendered.html_body
    assert "<script>" not in rendered.html_body
    assert url in rendered.text_body
