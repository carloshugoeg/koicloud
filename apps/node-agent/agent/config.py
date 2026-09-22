from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Runtime settings for the node-agent."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    internal_api_url: str = Field(
        default="http://127.0.0.1:8000/internal/v1",
        alias="INTERNAL_API_URL",
    )
    node_id: str = Field(default="node-dev", alias="NODE_ID")
    node_token: str = Field(default="change-me", alias="NODE_TOKEN")
    agent_mode: Literal["mock", "docker"] = Field(default="mock", alias="AGENT_MODE")
    poll_interval_seconds: float = Field(default=1.0, alias="POLL_INTERVAL_SECONDS")
    heartbeat_interval_seconds: float = Field(default=30.0, alias="HEARTBEAT_INTERVAL_SECONDS")
    backup_dir: Path = Field(default=Path("/tmp/koicloud/backups"), alias="BACKUP_DIR")
    mock_latency_ms: int = Field(default=0, alias="MOCK_LATENCY_MS")
    mock_default_size_bytes: int = Field(default=134_217_728, alias="MOCK_DEFAULT_SIZE_BYTES")


@lru_cache(maxsize=1)
def get_settings() -> AgentSettings:
    return AgentSettings()
