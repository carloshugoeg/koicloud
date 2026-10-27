"""apps/web/api/index.py serves the API only when VERCEL_ENV=preview (fail-closed)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

INDEX = Path(__file__).resolve().parents[2] / "web" / "api" / "index.py"


def _load_index(monkeypatch: pytest.MonkeyPatch, vercel_env: str | None):
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    if vercel_env is not None:
        monkeypatch.setenv("VERCEL_ENV", vercel_env)
    name = f"koi_preview_api_{vercel_env}_{id(object())}"
    spec = importlib.util.spec_from_file_location(name, INDEX)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


async def _post_login(app) -> tuple[int, bytes]:
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
    raw = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return start["status"], raw


@pytest.mark.asyncio
@pytest.mark.parametrize("vercel_env", ["production", "development", None, ""])
async def test_non_preview_entry_returns_404_json(
    monkeypatch: pytest.MonkeyPatch, vercel_env: str | None
) -> None:
    mod = _load_index(monkeypatch, vercel_env)
    assert mod._preview() is False
    status, raw = await _post_login(mod._get_app())
    assert status == 404
    assert b"Preview API is not available" in raw
    assert b"not_found" in raw
    assert b"pond_not_found" not in raw


def test_preview_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _load_index(monkeypatch, "preview")._preview() is True
    assert _load_index(monkeypatch, "production")._preview() is False
    assert _load_index(monkeypatch, None)._preview() is False


def test_read_body_over_max_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_index(monkeypatch, "production")

    class _Handler:
        headers = {"Content-Length": str(mod.MAX_BODY + 1)}

        class _Rfile:
            @staticmethod
            def read(_n: int) -> bytes:
                return b"x"

        rfile = _Rfile()

    with pytest.raises(mod.BodyTooLarge):
        mod._read_body(_Handler())  # type: ignore[arg-type]  # minimal stub for BaseHTTPRequestHandler
