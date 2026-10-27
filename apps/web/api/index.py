"""Preview-only KoiCloud API entry for Vercel (real apps/api FastAPI).

Vite + /api uses BaseHTTPRequestHandler serverless functions. This handler
restores the original path from ?koi_path=… and runs the FastAPI ASGI app.
Fail-closed: the real API runs only when VERCEL_ENV=preview.
Any other value (including production / unset) returns 404 JSON.
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

_LIB = Path(__file__).resolve().parent / "_koi_api"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

MAX_BODY = 1_000_000

_fastapi_app: Any | None = None
_loop: asyncio.AbstractEventLoop | None = None
_lifespan_started = False
# Vercel may invoke this sync handler concurrently on one warm worker.
# Serialise run_until_complete so we never hit "loop already running".
_loop_lock = threading.Lock()


def _preview() -> bool:
    """Serve the real API only on Vercel preview. Fail closed otherwise."""
    return (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview"


def _configure_preview_env() -> None:
    os.environ.setdefault("KOI_DB_SCHEMA", "koicloud")
    os.environ.setdefault("PAYMENT_PROVIDER", "simulated")
    os.environ.setdefault("AUTO_MICRO_SUBSCRIPTION", "true")
    sha = (os.environ.get("VERCEL_GIT_COMMIT_SHA") or "").strip()
    if sha:
        os.environ["APP_VERSION"] = sha
    unpooled = (os.environ.get("DATABASE_URL_UNPOOLED") or "").strip()
    if unpooled and not (os.environ.get("DATABASE_URL") or "").strip():
        os.environ["DATABASE_URL"] = unpooled


def _disabled_app() -> Any:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    disabled = FastAPI(title="KoiCloud API (disabled)")

    @disabled.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def off(full_path: str = "") -> JSONResponse:
        # Generic not-found shape (catalog-style). Not pond_not_found — this
        # path is the fail-closed preview entry, not a missing pond.
        return JSONResponse(
            status_code=404,
            content={
                "code": "not_found",
                "message": "Preview API is not available in this deployment",
                "request_id": None,
            },
        )

    return disabled


def _get_app() -> Any:
    global _fastapi_app
    if _fastapi_app is not None:
        return _fastapi_app
    if not _preview():
        _fastapi_app = _disabled_app()
        return _fastapi_app

    _configure_preview_env()
    from app.main import app as fastapi_app

    _fastapi_app = fastapi_app
    return _fastapi_app


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


async def _lifespan_startup(app: Any) -> None:
    """Run ASGI lifespan startup once so FastMCP streamable HTTP works."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    done = asyncio.Event()
    failed: list[str] = []

    async def receive() -> dict[str, Any]:
        return await queue.get()

    async def send(message: dict[str, Any]) -> None:
        msg_type = message.get("type")
        if msg_type == "lifespan.startup.complete":
            done.set()
        elif msg_type == "lifespan.startup.failed":
            failed.append(str(message.get("message") or "lifespan startup failed"))
            done.set()

    task = asyncio.create_task(
        app({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)
    )
    await queue.put({"type": "lifespan.startup"})
    await done.wait()
    if failed:
        task.cancel()
        raise RuntimeError(failed[0])
    # Keep the lifespan task running for the warm instance; do not cancel.


def _ensure_lifespan(app: Any) -> None:
    global _lifespan_started
    if _lifespan_started or not _preview():
        return
    with _loop_lock:
        if _lifespan_started:
            return
        loop = _get_loop()
        loop.run_until_complete(_lifespan_startup(app))
        _lifespan_started = True


def _run_coro(coro: Any) -> Any:
    with _loop_lock:
        return _get_loop().run_until_complete(coro)


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


class BodyTooLarge(Exception):
    """Request body exceeds MAX_BODY."""


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError:
        length = 0
    if length <= 0:
        return b""
    if length > MAX_BODY:
        raise BodyTooLarge()
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
    try:
        _ensure_lifespan(app)
    except Exception:
        traceback.print_exc()
        status = 500
        raw = (
            b'{"code":"internal_error","message":"Algo sali\\u00f3 mal, revis\\u00e1 los logs",'
            b'"request_id":null}'
        )
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(raw)))
        handler.end_headers()
        handler.wfile.write(raw)
        return

    path = _original_path(handler)
    query = _forward_query(handler)
    try:
        body = _read_body(handler)
    except BodyTooLarge:
        raw = b'{"message":"Request body too large","request_id":null}'
        handler.send_response(413)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(raw)))
        handler.end_headers()
        if handler.command != "HEAD":
            handler.wfile.write(raw)
        return

    headers: list[tuple[bytes, bytes]] = []
    for key, value in handler.headers.items():
        headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    if not any(k == b"host" for k, _ in headers):
        headers.append((b"host", b"vercel.app"))

    try:
        status, resp_headers, raw = _run_coro(
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
        traceback.print_exc()
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
