"""Unit checks for preview-only admin seed (no DB required)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_ensure_preview_admin_noops_outside_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_EMAIL", "admin@koicloud.dev")
    monkeypatch.setenv("KOI_PREVIEW_ADMIN_PASSWORD", "should-not-run")

    preview_seed = importlib.import_module("preview_seed")
    # Would raise ImportError if the body ran without apps/api vendored.
    preview_seed.ensure_preview_admin()


def test_ensure_preview_admin_noops_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.delenv("KOI_PREVIEW_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("KOI_PREVIEW_ADMIN_PASSWORD", raising=False)

    preview_seed = importlib.import_module("preview_seed")
    preview_seed.ensure_preview_admin()
