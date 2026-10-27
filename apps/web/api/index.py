"""Preview-only KoiCloud API entry for Vercel (real apps/api FastAPI).

Vite + /api uses BaseHTTPRequestHandler serverless functions. This handler
restores the original path from ?koi_path=… and runs the FastAPI ASGI app.
Production (VERCEL_ENV=production) always returns 404 JSON.
"""

from __future__ import annotations

import asyncio
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

_LIB = Path(__file__).resolve().parent / "_koi_api"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

MAX_BODY = 1_000_000


def _production() -> bool:
    return (os.environ.get("VERCEL_ENV") or "").strip().lower() == "production"


def _configure_preview_env() -> None:
    os.environ.setdefault("KOI_PREVIEW_MOCK", "1")
    os.environ.setdefault("KOI_DB_SCHEMA", "koicloud")
    os.environ.setdefault("PAYMENT_PROVIDER", "simulated")
    os.environ.setdefault("AUTO_MICRO_SUBSCRIPTION", "true")
    sha = (os.environ.get("VERCEL_GIT_COMMIT_SHA") or "").strip()
    if sha:
        os.environ["APP_VERSION"] = sha
    unpooled = (os.environ.get("DATABASE_URL_UNPOOLED") or "").strip()
    if unpooled and not (os.environ.get("DATABASE_URL") or "").strip():
        os.environ["DATABASE_URL"] = unpooled


_fastapi_app: Any | None = None


def _get_app() -> Any:
    global _fastapi_app
    if _fastapi_app is not None:
        return _fastapi_app
    if _production():
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        disabled = FastAPI(title="KoiCloud API (disabled)")

        @disabled.api_route(
            "/{full_path:path}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        )
        async def off(full_path: str = "") -> JSONResponse:
            return JSONResponse(
                status_code=404,
                content={
                    "code": "pond_not_found",
                    "message": "Preview API is not available in this deployment",
                    "request_id": None,
                },
            )

        _fastapi_app = disabled
        return _fastapi_app

    _configure_preview_env()
    from app.main import app as fastapi_app

    _fastapi_app = fastapi_app
    return _fastapi_app


def _original_path(handler: BaseHTTPRequestHandler) -> str:
    split = urlsplit(handler.path)
    query = parse_qs(split.query)
    forced = query.get("koi_path", [None])[0]
    if isinstance(forced, str) and forced.startswith("/"):
        return forced
    for header in (
        "x-forwarded-uri",
        "x-vercel-forwarded-path",
        "x-invoke-path",
        "x-matched-path",
    ):
        raw = handler.headers.get(header)
        if not raw:
            continue
        path = urlsplit(raw).path
        if path.startswith("/api/v1") or path == "/mcp" or path.startswith("/mcp/"):
            return path
    path = split.path
    if path.startswith("/api/v1") or path == "/mcp":
        return path
    return path


def _forward_query(handler: BaseHTTPRequestHandler) -> str:
    split = urlsplit(handler.path)
    query = parse_qs(split.query)
    kept: list[str] = []
    for key, values in query.items():
        if key == "koi_path":
            continue
        for value in values:
            kept.append(f"{key}={value}")
    return "&".join(kept)


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError:
        length = 0
    if length <= 0:
        return b""
    if length > MAX_BODY:
        return b""
    return handler.rfile.read(length)


async def _run_asgi(
    app: Any,
    *,
    method: str,
    path: str,
    query: str,
    headers: list[tuple[bytes, bytes]],
    body: bytes,
) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    status_code = 500
    response_headers: list[tuple[bytes, bytes]] = []
    chunks: list[bytes] = []
    body_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.disconnect"}
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal status_code, response_headers
        if message["type"] == "http.response.start":
            status_code = int(message["status"])
            response_headers = list(message.get("headers") or [])
        elif message["type"] == "http.response.body":
            chunk = message.get("body") or b""
            if chunk:
                chunks.append(chunk)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query.encode("latin-1"),
        "headers": headers,
        "client": ("127.0.0.1", 0),
        "server": ("vercel", 443),
        "root_path": "",
    }
    await app(scope, receive, send)
    return status_code, response_headers, b"".join(chunks)


def _serve(handler: BaseHTTPRequestHandler) -> None:
    app = _get_app()
    path = _original_path(handler)
    query = _forward_query(handler)
    body = _read_body(handler)
    headers: list[tuple[bytes, bytes]] = []
    for key, value in handler.headers.items():
        headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    # Ensure host present for URL builders.
    if not any(k == b"host" for k, _ in headers):
        headers.append((b"host", b"vercel.app"))

    try:
        status, resp_headers, raw = asyncio.run(
            _run_asgi(
                app,
                method=handler.command,
                path=path,
                query=query,
                headers=headers,
                body=body,
            )
        )
    except Exception:
        status = 500
        raw = (
            b'{"code":"internal_error","message":"Algo sali\\u00f3 mal, revis\\u00e1 los logs",'
            b'"request_id":null}'
        )
        resp_headers = [(b"content-type", b"application/json")]

    handler.send_response(status)
    sent_length = False
    for key, value in resp_headers:
        name = key.decode("latin-1")
        if name.lower() == "content-length":
            sent_length = True
        if name.lower() == "transfer-encoding":
            continue
        handler.send_header(name, value.decode("latin-1"))
    if not sent_length:
        handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    if raw and handler.command != "HEAD":
        handler.wfile.write(raw)


class handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        _serve(self)

    def do_POST(self) -> None:
        _serve(self)

    def do_PUT(self) -> None:
        _serve(self)

    def do_PATCH(self) -> None:
        _serve(self)

    def do_DELETE(self) -> None:
        _serve(self)

    def do_OPTIONS(self) -> None:
        _serve(self)

    def do_HEAD(self) -> None:
        _serve(self)
