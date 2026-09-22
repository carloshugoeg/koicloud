from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "koicloud" / "config.json"


class CliConfig(BaseModel):
    """Persisted local CLI configuration."""

    base_url: str = DEFAULT_BASE_URL
    access_token: str | None = None
    refresh_token: str | None = None
    user: dict[str, object] | None = None


class CliSettings(BaseSettings):
    """Runtime settings resolved from environment variables."""

    model_config = SettingsConfigDict(env_prefix="KOICLOUD_", extra="ignore")

    base_url: str = DEFAULT_BASE_URL
    config_path: Path = DEFAULT_CONFIG_PATH


@lru_cache(maxsize=1)
def get_settings() -> CliSettings:
    return CliSettings()


def load_config(settings: CliSettings | None = None) -> CliConfig:
    settings = settings or get_settings()
    path = settings.config_path
    if not path.exists():
        return CliConfig(base_url=settings.base_url)

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return CliConfig(base_url=settings.base_url)

    config = CliConfig.model_validate_json(raw)
    if not config.base_url:
        config = config.model_copy(update={"base_url": settings.base_url})
    return config


def save_config(config: CliConfig, settings: CliSettings | None = None) -> Path:
    settings = settings or get_settings()
    path = settings.config_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    return path


def clear_config(settings: CliSettings | None = None) -> None:
    settings = settings or get_settings()
    try:
        settings.config_path.unlink()
    except FileNotFoundError:
        return
