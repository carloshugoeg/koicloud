"""EMAIL_PROVIDER startup rules and verify-token log gating."""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from app.commands.auth import _log_verify_token_if_console
from app.core.config import Settings, get_settings
from app.main import create_app


def test_settings_reads_email_provider_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("ENVIRONMENT", "development")
    settings = Settings()
    assert settings.email_provider == "resend"


def test_production_with_console_email_provider_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="EMAIL_PROVIDER=console"):
        Settings(environment="production", email_provider="console")


def test_prod_alias_with_console_email_provider_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="EMAIL_PROVIDER=console"):
        Settings(environment="prod", email_provider="console")


def test_production_with_non_console_email_provider_starts() -> None:
    settings = Settings(environment="production", email_provider="resend")
    assert settings.email_provider == "resend"
    assert settings.environment == "production"


def test_create_app_refuses_prod_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    with pytest.raises(ValidationError, match="EMAIL_PROVIDER=console"):
        create_app()
    get_settings.cache_clear()


def test_unset_environment_defaults_to_development_and_allows_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prod compose must pin ENVIRONMENT=production; without it the guard is a no-op."""
    get_settings.cache_clear()
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    settings = Settings()
    assert settings.environment == "development"
    assert settings.email_provider == "console"
    get_settings.cache_clear()


def test_production_env_from_environ_with_console_refuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same path a prod container hits once compose sets ENVIRONMENT=production."""
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    with pytest.raises(ValidationError, match="EMAIL_PROVIDER=console"):
        Settings()
    get_settings.cache_clear()


def test_verify_token_not_logged_when_email_provider_is_not_console(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()

    with caplog.at_level(logging.INFO, logger="app.commands.auth"):
        _log_verify_token_if_console("user@example.com", "verify_secret_should_not_appear")

    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "verify_email token" not in joined
    assert "verify_secret_should_not_appear" not in joined
    get_settings.cache_clear()


def test_verify_token_logged_when_email_provider_is_console(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()

    with caplog.at_level(logging.INFO, logger="app.commands.auth"):
        _log_verify_token_if_console("user@example.com", "verify_token_console_ok")

    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "verify_email token for user@example.com: verify_token_console_ok" in joined
    get_settings.cache_clear()
