from __future__ import annotations

from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    app_name: str = "KoiCloud API"
    app_version: str = "0.1.0"
    environment: str = "development"

    api_prefix: str = "/api/v1"
    internal_api_prefix: str = "/internal/v1"
    mcp_prefix: str = "/mcp"

    database_url: str = "postgresql+asyncpg://koicloud:koicloud@localhost:5432/koicloud"
    jwt_secret: str = "koicloud-dev-jwt-secret-change-me"
    access_token_ttl_minutes: int = 15
    refresh_ttl_days: int = 30
    confirm_ttl_seconds: int = 300
    pond_password_key: str = "7chvGNh8l4rbVgpH0wWJjCT2J8eQ6D8eW5DiKjR3owE="

    koicloud_domain: str = "koicloud.local"
    node_public_host: str = "db.koicloud.local"
    node_id: str = "node-sv-01"
    node_token: str = "koicloud-node-token"
    pond_port_range_start: int = 15000
    pond_port_range_end: int = 15999
    node_stale_seconds: int = 90
    auto_micro_subscription: bool = True
    payment_provider: str = "simulated"
    # Read from EMAIL_PROVIDER. Dev/e2e use console; production must not.
    email_provider: str = "console"
    invoice_dir: str = "/var/lib/koicloud/invoices"
    backup_dir: str = "/var/lib/koicloud/backups"
    mcp_enabled: bool = True
    mcp_demo_slug: str = "demo-agent"
    mcp_demo_password: str = "koicloud-demo"

    # Preview Neon schema (search_path). Applied only when VERCEL_ENV=preview.
    koi_db_schema: str = ""

    default_limit: int = Field(default=50, ge=1, le=100)

    @model_validator(mode="after")
    def reject_console_email_in_production(self) -> Self:
        env = self.environment.strip().lower()
        provider = self.email_provider.strip().lower()
        if env in {"production", "prod"} and provider == "console":
            raise ValueError(
                "EMAIL_PROVIDER=console is not allowed when ENVIRONMENT is production"
            )
        return self

    @model_validator(mode="after")
    def reject_default_secrets_in_production(self) -> Self:
        """Refuse built-in defaults and change-me placeholders in production."""
        env = self.environment.strip().lower()
        if env not in {"production", "prod"}:
            return self
        guards = (
            ("jwt_secret", "JWT_SECRET", "koicloud-dev-jwt-secret-change-me"),
            (
                "pond_password_key",
                "POND_PASSWORD_KEY",
                "7chvGNh8l4rbVgpH0wWJjCT2J8eQ6D8eW5DiKjR3owE=",
            ),
            ("node_token", "NODE_TOKEN", "koicloud-node-token"),
            ("mcp_demo_password", "MCP_DEMO_PASSWORD", "koicloud-demo"),
        )
        offenders: list[str] = []
        for attr, env_name, builtin in guards:
            value: str = getattr(self, attr)
            if value == builtin or value.startswith("change-me"):
                offenders.append(env_name)
        if offenders:
            joined = ", ".join(offenders)
            raise ValueError(
                f"{joined} must not use the built-in default or a change-me placeholder "
                "when ENVIRONMENT is production"
            )
        return self


def to_sync_database_url(url: str) -> str:
    """Alembic uses a sync engine; asyncpg URLs raise MissingGreenlet."""
    replacements = (
        ("postgresql+asyncpg://", "postgresql+psycopg://"),
        ("postgres+asyncpg://", "postgresql+psycopg://"),
    )
    for old, new in replacements:
        if url.startswith(old):
            url = new + url[len(old) :]
            break
    # asyncpg uses `ssl=require`; psycopg expects `sslmode=require`.
    if "sslmode=" not in url:
        url = url.replace("ssl=require", "sslmode=require").replace("ssl=true", "sslmode=require")
    return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

