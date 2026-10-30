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


def test_development_still_allows_builtin_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # CI injects JWT_SECRET/NODE_TOKEN; clear them so Field defaults apply.
    for name in (
        "JWT_SECRET",
        "POND_PASSWORD_KEY",
        "NODE_TOKEN",
        "MCP_DEMO_PASSWORD",
        "ENVIRONMENT",
        "EMAIL_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
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


# Compose prod fallbacks. Each value starts with change-me and is not a built-in default.
_CHANGE_ME_PREFIX_SECRETS = (
    ("jwt_secret", "JWT_SECRET", "change-me-32-random-bytes"),
    ("node_token", "NODE_TOKEN", "change-me"),
    ("pond_password_key", "POND_PASSWORD_KEY", "change-me-fernet-key"),
    ("mcp_demo_password", "MCP_DEMO_PASSWORD", "change-me-mcp-demo"),
)


@pytest.mark.parametrize(
    ("field", "env_name", "placeholder"),
    _CHANGE_ME_PREFIX_SECRETS,
    ids=[item[1] for item in _CHANGE_ME_PREFIX_SECRETS],
)
def test_production_rejects_secret_that_starts_with_change_me(
    field: str,
    env_name: str,
    placeholder: str,
) -> None:
    with pytest.raises(ValidationError, match=env_name):
        Settings(**{**_PROD_SAFE, field: placeholder})


def test_production_allows_secret_that_mentions_change_me_only_later() -> None:
    token = "prod-node-token-change-me-suffix"
    settings = Settings(**{**_PROD_SAFE, "node_token": token})
    assert settings.node_token == token


def test_production_hides_openapi_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.main import create_app

    get_settings.cache_clear()
    for name in (
        "JWT_SECRET",
        "POND_PASSWORD_KEY",
        "NODE_TOKEN",
        "MCP_DEMO_PASSWORD",
        "ENVIRONMENT",
        "EMAIL_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("JWT_SECRET", _PROD_SAFE["jwt_secret"])
    monkeypatch.setenv("POND_PASSWORD_KEY", _PROD_SAFE["pond_password_key"])
    monkeypatch.setenv("NODE_TOKEN", _PROD_SAFE["node_token"])
    monkeypatch.setenv("MCP_DEMO_PASSWORD", _PROD_SAFE["mcp_demo_password"])
    try:
        app = create_app()
    finally:
        get_settings.cache_clear()
    assert (app.docs_url, app.openapi_url) == (None, None)
