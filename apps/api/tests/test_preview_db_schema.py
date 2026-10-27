"""Preview schema search_path must not change production / non-preview DB setup."""

from __future__ import annotations

from pathlib import Path

from app.core.db import resolve_preview_schema


def test_non_preview_ignores_koi_db_schema() -> None:
    """Prod / CI / local: even with a schema name, resolve returns empty (main behavior)."""
    assert resolve_preview_schema(vercel_env=None, schema="koicloud") == ""
    assert resolve_preview_schema(vercel_env="", schema="koicloud") == ""
    assert resolve_preview_schema(vercel_env="development", schema="koicloud") == ""


def test_production_vercel_env_ignores_schema() -> None:
    assert resolve_preview_schema(vercel_env="production", schema="koicloud") == ""


def test_preview_applies_schema() -> None:
    assert resolve_preview_schema(vercel_env="preview", schema="koicloud") == "koicloud"
    assert resolve_preview_schema(vercel_env="preview", schema="  koicloud  ") == "koicloud"
    assert resolve_preview_schema(vercel_env="preview", schema="") == ""


def test_alembic_env_has_no_preview_schema_hooks() -> None:
    """Preview-infra must not touch Alembic migration setup."""
    text = (Path(__file__).resolve().parents[1] / "alembic" / "env.py").read_text()
    assert "KOI_DB_SCHEMA" not in text
    assert "search_path" not in text
    assert "koi_db_schema" not in text
