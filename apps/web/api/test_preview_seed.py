"""Unit checks for preview-only admin seed (no DB required)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _reload_seed():
    if "preview_seed" in sys.modules:
        return importlib.reload(sys.modules["preview_seed"])
    return importlib.import_module("preview_seed")


def test_ensure_preview_admin_noops_when_vercel_env_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("KOI_PREVIEW_SEED", "1")
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_EMAIL", "admin@koicloud.dev")
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_PASSWORD", "should-not-run")

    preview_seed = _reload_seed()
    # Would raise ImportError if the body ran without apps/api vendored.
    preview_seed.ensure_preview_admin()


def test_ensure_preview_admin_noops_when_vercel_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.setenv("KOI_PREVIEW_SEED", "1")
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_EMAIL", "admin@koicloud.dev")
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_PASSWORD", "should-not-run")

    preview_seed = _reload_seed()
    preview_seed.ensure_preview_admin()


def test_ensure_preview_admin_noops_without_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.delenv("KOI_PREVIEW_SEED", raising=False)
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_EMAIL", "admin@koicloud.dev")
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_PASSWORD", "should-not-run")

    preview_seed = _reload_seed()
    preview_seed.ensure_preview_admin()


def test_ensure_preview_admin_noops_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("KOI_PREVIEW_SEED", "1")
    monkeypatch.delenv("KOI_PREVIEW_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("KOI_PREVIEW_ADMIN_PASSWORD", raising=False)

    preview_seed = _reload_seed()
    preview_seed.ensure_preview_admin()


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://u:p@ep-prod-xyz.aws.neon.tech/koicloud",
        "postgresql://u:p@db.koicloud.dev:5432/koicloud",
        "postgresql://u:p@primary.cluster.example/koicloud",
        "",
    ],
)
def test_database_url_looks_like_production(url: str) -> None:
    preview_seed = _reload_seed()
    assert preview_seed._database_url_looks_like_production(url) is True


def test_database_url_allows_preview_scratch() -> None:
    preview_seed = _reload_seed()
    url = "postgresql+asyncpg://u:p@ep-soft-haze-a1b2c3d4.us-east-2.aws.neon.tech/neondb"
    assert preview_seed._database_url_looks_like_production(url) is False
