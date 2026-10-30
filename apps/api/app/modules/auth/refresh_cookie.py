from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.modules.auth.service import REFRESH_COOKIE


def refresh_body_from_cookie(body: bytes, cookie: str | None) -> bytes | None:
    """Fill an empty refresh body from the httpOnly cookie. A body token wins."""
    if not cookie:
        return None
    stripped = body.strip()
    if stripped in (b"", b"null"):
        return _token_body(cookie)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    token = payload.get("refresh_token")
    if isinstance(token, str) and token:
        return None
    return _token_body(cookie)


class RefreshCookieMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        if scope.get("path") != f"{get_settings().api_prefix}/auth/refresh":
            await self.app(scope, receive, send)
            return

        body = await _read_body(receive)
        replacement = refresh_body_from_cookie(body, _cookie(scope, REFRESH_COOKIE))
        if replacement is not None:
            body = replacement
            _set_header(scope, b"content-type", b"application/json")
            _set_header(scope, b"content-length", str(len(body)).encode())

        sent = False

        async def replay() -> Message:
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send_and_clear(message: Message) -> None:
            if message["type"] == "http.response.start" and message["status"] in (401, 403):
                headers = list(message.get("headers") or [])
                headers.append((b"set-cookie", _clear_cookie()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, replay, send_and_clear)


def _token_body(cookie: str) -> bytes:
    return json.dumps({"refresh_token": cookie}).encode()


def _clear_cookie() -> bytes:
    path = get_settings().api_prefix
    return f"{REFRESH_COOKIE}=; Max-Age=0; Path={path}; HttpOnly; SameSite=lax".encode()


def _header(scope: Scope, name: bytes) -> bytes | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value
    return None


def _set_header(scope: Scope, name: bytes, value: bytes) -> None:
    headers = [(key, item) for key, item in scope.get("headers", []) if key.lower() != name]
    headers.append((name, value))
    scope["headers"] = headers


def _cookie(scope: Scope, name: str) -> str | None:
    raw = _header(scope, b"cookie")
    if raw is None:
        return None
    prefix = f"{name}="
    for part in raw.decode().split(";"):
        item = part.strip()
        if item.startswith(prefix):
            return item[len(prefix) :]
    return None


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)
