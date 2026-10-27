"""Preview-only KoiCloud sim entry for Vercel.

Rewrites send /mcp and /api/v1/* here. Production (VERCEL_ENV=production) always
returns 404 JSON — never HTML, never the in-memory sim. Local ThreadingHTTPServer
in e2e/sim-backend stays the canonical long-running process for loopback seeds.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_LIB = Path(__file__).resolve().parent / "_koi_sim"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from app import dispatch  # noqa: E402
from state import SimError  # noqa: E402

MAX_BODY = 1_000_000
_configure_done = False


def _ensure_runtime() -> None:
    global _configure_done
    if _configure_done:
        return
    _configure_persist()
    _configure_done = True


def _sim_enabled() -> bool:
    env = (os.environ.get("VERCEL_ENV") or "").strip().lower()
    if env == "production":
        return False
    if os.environ.get("KOI_PREVIEW_SIM", "").strip() == "0":
        return False
    # Preview deployments, and local `vercel dev` without VERCEL_ENV.
    return env in {"preview", "development", ""} or os.environ.get("KOI_PREVIEW_SIM") == "1"


def _configure_persist() -> None:
    # Prefer Vercel Blob (BLOB_READ_WRITE_TOKEN). Fall back to /tmp for warm instances.
    if not os.environ.get("KOI_SIM_PERSIST_PATH"):
        deploy = (os.environ.get("VERCEL_DEPLOYMENT_ID") or "local").strip()
        os.environ["KOI_SIM_PERSIST_PATH"] = f"/tmp/koi-sim-{deploy}.pkl"


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
        if path.startswith("/api/v1") or path == "/mcp":
            return path
    path = split.path
    if path.startswith("/api/v1") or path == "/mcp":
        return path
    return path


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError:
        length = 0
    if length < 0 or length > MAX_BODY:
        raise SimError("token_invalid", message="Solicitud inválida")
    if length == 0:
        return b""
    return handler.rfile.read(length)


def _send(handler: BaseHTTPRequestHandler, status: int, payload: dict | None) -> None:
    raw = b"" if payload is None else json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header(
        "Access-Control-Allow-Headers",
        "Authorization, Content-Type, X-KOI-Surface, X-KOI-Confirm-Token, "
        "X-KOI-Agent-Password, Idempotency-Key, Accept, MCP-Protocol-Version, "
        "Mcp-Session-Id",
    )
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    path = _original_path(handler)
    if handler.command == "POST" and path == "/mcp":
        session = handler.headers.get("Mcp-Session-Id") or "sim-session"
        handler.send_header("Mcp-Session-Id", session)
    handler.end_headers()
    if raw:
        handler.wfile.write(raw)


def _serve(handler: BaseHTTPRequestHandler) -> None:
    if not _sim_enabled():
        _send(
            handler,
            404,
            {
                "code": "pond_not_found",
                "message": "Preview sim is not available in this deployment",
                "request_id": None,
            },
        )
        return
    _ensure_runtime()
    try:
        body = _read_body(handler)
        headers = {key.lower(): value for key, value in handler.headers.items()}
        path = _original_path(handler)
        split = urlsplit(handler.path)
        headers["x-koi-raw-query"] = split.query
        status, payload = dispatch(handler.command, path, headers, body)
    except SimError as exc:
        status = exc.status
        payload = exc.body()
    except Exception:
        status = 500
        payload = {
            "code": "internal_error",
            "message": "Algo salió mal, revisá los logs",
            "request_id": None,
        }
    _send(handler, status, payload)


class handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        _serve(self)

    def do_POST(self) -> None:
        _serve(self)

    def do_DELETE(self) -> None:
        _serve(self)

    def do_OPTIONS(self) -> None:
        _serve(self)
