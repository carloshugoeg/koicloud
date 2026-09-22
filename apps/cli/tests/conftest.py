from __future__ import annotations

from collections.abc import Callable

import pytest
from typer.testing import CliRunner

from koicloud_cli.config import CliConfig, get_settings, save_config


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_cli_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    config_path = tmp_path / "koicloud-config.json"
    monkeypatch.setenv("KOICLOUD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("KOICLOUD_BASE_URL", "https://koicloud.test/api/v1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def write_logged_in_config() -> Callable[[], CliConfig]:
    def _write() -> CliConfig:
        config = CliConfig(
            base_url="https://koicloud.test/api/v1",
            access_token="access-token",
            refresh_token="refresh-token",
            user={"email": "demo@koicloud.dev"},
        )
        save_config(config)
        return config

    return _write
