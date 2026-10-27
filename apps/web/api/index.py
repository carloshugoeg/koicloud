"""Preview-only KoiCloud API entry for Vercel (real apps/api FastAPI).

Rewrites send /mcp and /api/v1/* here with ?koi_path=… so FastAPI sees the
original path. Production (VERCEL_ENV=production) always returns 404 JSON.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

_LIB = Path(__file__).resolve().parent / "_koi_api"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))


def _production_disabled() -> Any:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    disabled = FastAPI(title="KoiCloud API (disabled)")

    @disabled.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def off(request: Request, full_path: str = "") -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "code": "pond_not_found",
                "message": "Preview API is not available in this deployment",
                "request_id": None,
            },
        )

    return disabled


def _configure_preview_env() -> None:
    os.environ.setdefault("KOI_PREVIEW_MOCK", "1")
    os.environ.setdefault("KOI_DB_SCHEMA", "koicloud")
    os.environ.setdefault("PAYMENT_PROVIDER", "simulated")
    os.environ.setdefault("AUTO_MICRO_SUBSCRIPTION", "true")
    sha = (os.environ.get("VERCEL_GIT_COMMIT_SHA") or "").strip()
    if sha:
        os.environ["APP_VERSION"] = sha
    # Prefer unpooled when present (Alembic / DDL); else DATABASE_URL.
    unpooled = (os.environ.get("DATABASE_URL_UNPOOLED") or "").strip()
    if unpooled and not (os.environ.get("DATABASE_URL") or "").strip():
        os.environ["DATABASE_URL"] = unpooled


def _restore_path(scope: dict[str, Any]) -> dict[str, Any]:
    if scope.get("type") != "http":
        return scope
    raw_path = scope.get("path") or ""
    query = scope.get("query_string", b"").decode("latin-1")
    params = parse_qs(query)
    forced = params.get("koi_path", [None])[0]
    if isinstance(forced, str) and forced.startswith("/"):
        new_scope = dict(scope)
        new_scope["path"] = forced
        # Drop koi_path from the query FastAPI sees.
        kept = []
        for key, values in params.items():
            if key == "koi_path":
                continue
            for value in values:
                kept.append(f"{key}={value}")
        new_scope["query_string"] = "&".join(kept).encode("latin-1")
        return new_scope

    headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }
    for header in (
        "x-forwarded-uri",
        "x-vercel-forwarded-path",
        "x-invoke-path",
        "x-matched-path",
    ):
        raw = headers.get(header)
        if not raw:
            continue
        path = urlsplit(raw).path
        if path.startswith("/api/v1") or path == "/mcp" or path.startswith("/mcp/"):
            new_scope = dict(scope)
            new_scope["path"] = path
            return new_scope

    if raw_path.startswith("/api/v1") or raw_path == "/mcp":
        return scope
    return scope


class _PathRewriteASGI:
    def __init__(self, inner: Any) -> None:
        self.inner = inner

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        await self.inner(_restore_path(scope), receive, send)

    def __getattr__(self, item: str) -> Any:
        return getattr(self.inner, item)


def _preview_app() -> Any:
    _configure_preview_env()
    from app.main import app as fastapi_app

    return _PathRewriteASGI(fastapi_app)


_env = (os.environ.get("VERCEL_ENV") or "").strip().lower()
if _env == "production":
    app = _production_disabled()
else:
    app = _preview_app()
