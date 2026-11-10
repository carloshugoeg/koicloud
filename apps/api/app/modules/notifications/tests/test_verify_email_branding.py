from collections.abc import Iterator
from html import escape

import pytest

from app.core.config import get_settings
from app.modules.notifications.templates import render_template

VERIFY_URL = "https://app.koicloud.dev/verify-email?token=sample-token-not-real"
PUBLIC_LOGO = "https://koicloud-web.vercel.app/koi/koi-mark-32.png"
RESET_URL = "https://ponds.example/reset?token=sample-token-not-real"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _use_domain(monkeypatch: pytest.MonkeyPatch, domain: str) -> None:
    monkeypatch.setenv("KOICLOUD_DOMAIN", domain)
    get_settings.cache_clear()


def test_verify_email_has_branding_and_plain_text_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_domain(monkeypatch, "koicloud.local")
    rendered = render_template(
        "verify_email", {"url": VERIFY_URL, "email": "demo@example.invalid"}
    )
    assert rendered.subject == "Verificá tu correo"
    assert f'href="{VERIFY_URL}"' in rendered.html_body
    assert VERIFY_URL in rendered.text_body
    assert "KoiCloud" in rendered.html_body
    assert "#0A6D64" in rendered.html_body
    assert f'src="{PUBLIC_LOGO}"' in rendered.html_body
    assert "app.koicloud.dev/koi/" not in rendered.html_body
    assert "KoiCloud · PaaS de datos" in rendered.html_body
    assert "24 horas" in rendered.html_body
    assert "ignorar" in rendered.html_body


@pytest.mark.parametrize(
    ("domain", "logo_src"),
    [
        ("koicloud.local", PUBLIC_LOGO),
        ("", PUBLIC_LOGO),
        ("local", PUBLIC_LOGO),
        ("localhost", PUBLIC_LOGO),
        ("ponds.example", "https://ponds.example/koi/koi-mark-32.png"),
    ],
)
@pytest.mark.parametrize("template", ["verify_email", "reset_password"])
def test_logo_src_follows_koicloud_domain(
    monkeypatch: pytest.MonkeyPatch,
    domain: str,
    logo_src: str,
    template: str,
) -> None:
    _use_domain(monkeypatch, domain)
    rendered = render_template(
        template, {"url": VERIFY_URL, "email": "demo@example.invalid"}
    )
    assert f'src="{logo_src}"' in rendered.html_body
    assert "app.koicloud.dev/koi/" not in rendered.html_body


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


def test_reset_password_has_branding_and_plain_text_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_domain(monkeypatch, "ponds.example")
    rendered = render_template(
        "reset_password", {"url": RESET_URL, "email": "demo@example.invalid"}
    )
    assert rendered.subject == "Restablecé tu contraseña"
    assert f'href="{RESET_URL}"' in rendered.html_body
    assert RESET_URL in rendered.text_body
    assert "#0A6D64" in rendered.html_body
    assert 'src="https://ponds.example/koi/koi-mark-32.png"' in rendered.html_body
    assert "KoiCloud · PaaS de datos" in rendered.html_body
    assert "KoiCloud · PaaS de datos" in rendered.text_body
    assert "1 hora" in rendered.html_body
    assert "ignorar" in rendered.html_body


def test_reset_password_escapes_user_email() -> None:
    email = "<script>alert(1)</script>@x.test"
    rendered = render_template("reset_password", {"url": RESET_URL, "email": email})
    assert "<script>" not in rendered.html_body
    assert escape(email, quote=True) in rendered.html_body
    assert email in rendered.text_body


def test_reset_password_escapes_url_attribute_and_display_text() -> None:
    url = RESET_URL + '&next="onclick="alert(1)<script>'
    rendered = render_template(
        "reset_password", {"url": url, "email": "demo@example.invalid"}
    )
    safe_url = escape(url, quote=True)
    assert f'href="{safe_url}"' in rendered.html_body
    assert f">{safe_url}</a>" in rendered.html_body
    assert url not in rendered.html_body
    assert "<script>" not in rendered.html_body
    assert url in rendered.text_body
