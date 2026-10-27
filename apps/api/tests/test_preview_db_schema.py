"""Preview schema search_path must not change production / non-preview DB setup."""

from __future__ import annotations

import importlib

import pytest


def _reload_db(monkeypatch: pytest.MonkeyPatch, *, vercel_env: str | None, schema: str) -> object:
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    if vercel_env is not None:
        monkeypatch.setenv("VERCEL_ENV", vercel_env)
    monkeypatch.setenv("KOI_DB_SCHEMA", schema)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://koicloud:koicloud@localhost:5432/koicloud",
    )
    import app.core.config as config_mod

    config_mod.get_settings.cache_clear()
    import app.core.db as db_mod

    return importlib.reload(db_mod)


def test_non_preview_ignores_koi_db_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prod / CI / local: even with KOI_DB_SCHEMA set, connect_args stay empty (main behavior)."""
    db_mod = _reload_db(monkeypatch, vercel_env=None, schema="koicloud")
    assert db_mod._schema == ""
    assert db_mod._connect_args == {}


def test_production_vercel_env_ignores_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    db_mod = _reload_db(monkeypatch, vercel_env="production", schema="koicloud")
    assert db_mod._schema == ""
    assert db_mod._connect_args == {}


def test_preview_applies_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    db_mod = _reload_db(monkeypatch, vercel_env="preview", schema="koicloud")
    assert db_mod._schema == "koicloud"
    assert db_mod._connect_args == {"server_settings": {"search_path": "koicloud"}}


def test_alembic_env_has_no_preview_schema_hooks() -> None:
    """Preview-infra must not touch Alembic migration setup."""
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "alembic" / "env.py").read_text()
    assert "KOI_DB_SCHEMA" not in text
    assert "search_path" not in text
    assert "koi_db_schema" not in text
