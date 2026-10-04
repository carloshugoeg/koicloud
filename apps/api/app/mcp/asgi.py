from __future__ import annotations

from typing import Any

from starlette.middleware import Middleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.mcp.gate import McpGateMiddleware
from app.mcp.server import mcp

# Streamable HTTP ASGI app for IDE clients. OpenAPI GET/POST /mcp stay on FastAPI.
mcp_stream_app = mcp.http_app(
    path="/",
    transport="streamable-http",
    stateless_http=True,
    middleware=[Middleware(McpGateMiddleware)],
)


class McpHybridASGI:
    """Route Streamable HTTP (Accept: text/event-stream) to FastMCP; else FastAPI.

    Proxies attribute access to the FastAPI app so OpenAPI export and TestClient
    lifespan keep working (`app.openapi()`, `app.router`, …).
    """

    def __init__(self, fastapi_app: ASGIApp, stream_app: ASGIApp) -> None:
        self.fastapi_app = fastapi_app
        self.stream_app = stream_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.fastapi_app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        accept = headers.get("accept", "")
        wants_stream = "text/event-stream" in accept or "mcp-protocol-version" in headers

        if path.rstrip("/") == "/mcp" and method == "POST" and wants_stream:
            # FastMCP http_app is mounted at path="/"; strip /mcp prefix for it.
            stream_scope = dict(scope)
            stream_scope["path"] = "/"
            root = scope.get("root_path", "")
            stream_scope["root_path"] = f"{root}/mcp"
            await self.stream_app(stream_scope, receive, send)
            return

        await self.fastapi_app(scope, receive, send)

    def __getattr__(self, item: str) -> Any:
        return getattr(self.fastapi_app, item)


def wrap_with_mcp_stream(fastapi_app: ASGIApp) -> McpHybridASGI:
    return McpHybridASGI(fastapi_app, mcp_stream_app)
