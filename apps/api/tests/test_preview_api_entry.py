"""apps/web/api/index.py must 404 when VERCEL_ENV=production."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

INDEX = Path(__file__).resolve().parents[2] / "web" / "api" / "index.py"


def _load_index(monkeypatch: pytest.MonkeyPatch, vercel_env: str):
    monkeypatch.setenv("VERCEL_ENV", vercel_env)
    name = f"koi_preview_api_{vercel_env}_{id(object())}"
    spec = importlib.util.spec_from_file_location(name, INDEX)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_production_entry_returns_404_json(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_index(monkeypatch, "production")
    app = mod._get_app()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login",
        "query_string": b"",
        "headers": [(b"host", b"example.vercel.app"), (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 123),
        "server": ("example.vercel.app", 443),
    }
    body = b'{"email":"x@y.z","password":"xxxxxxxx"}'
    messages: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    await app(scope, receive, send)
    start = next(m for m in messages if m["type"] == "http.response.start")
    assert start["status"] == 404
    raw = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    assert b"Preview API is not available" in raw
    assert b"pond_not_found" in raw


def test_production_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_index(monkeypatch, "production")
    assert mod._production() is True
    mod2 = _load_index(monkeypatch, "preview")
    assert mod2._production() is False
