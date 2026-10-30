"""Production must refuse built-in default secrets at Settings load."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


_PROD_SAFE = {
    "environment": "production",
    "email_provider": "resend",
    "jwt_secret": "prod-jwt-secret-not-the-builtin-default-value",
    "pond_password_key": "prod-fernet-key-not-the-builtin-default==",
    "node_token": "prod-node-token-not-builtin",
    "mcp_demo_password": "prod-mcp-demo-password-not-builtin",
}


def test_production_with_default_jwt_secret_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(**{**_PROD_SAFE, "jwt_secret": "koicloud-dev-jwt-secret-change-me"})


def test_production_with_default_pond_password_key_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="POND_PASSWORD_KEY"):
        Settings(
            **{
                **_PROD_SAFE,
                "pond_password_key": "7chvGNh8l4rbVgpH0wWJjCT2J8eQ6D8eW5DiKjR3owE=",
            }
        )


def test_production_with_default_node_token_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="NODE_TOKEN"):
        Settings(**{**_PROD_SAFE, "node_token": "koicloud-node-token"})


def test_production_with_default_mcp_demo_password_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="MCP_DEMO_PASSWORD"):
        Settings(**{**_PROD_SAFE, "mcp_demo_password": "koicloud-demo"})


def test_production_with_non_default_secrets_starts() -> None:
    settings = Settings(**_PROD_SAFE)
    assert settings.environment == "production"
    assert settings.jwt_secret == _PROD_SAFE["jwt_secret"]
    assert settings.node_token == _PROD_SAFE["node_token"]


def test_development_still_allows_builtin_defaults() -> None:
    settings = Settings(environment="development", email_provider="console")
    assert settings.jwt_secret == "koicloud-dev-jwt-secret-change-me"
    assert settings.node_token == "koicloud-node-token"
    assert settings.mcp_demo_password == "koicloud-demo"


def test_create_app_path_refuses_prod_default_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.main import create_app

    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("JWT_SECRET", "koicloud-dev-jwt-secret-change-me")
    monkeypatch.setenv("POND_PASSWORD_KEY", _PROD_SAFE["pond_password_key"])
    monkeypatch.setenv("NODE_TOKEN", _PROD_SAFE["node_token"])
    monkeypatch.setenv("MCP_DEMO_PASSWORD", _PROD_SAFE["mcp_demo_password"])
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        create_app()
    get_settings.cache_clear()
