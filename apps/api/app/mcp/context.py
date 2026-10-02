from __future__ import annotations

from contextvars import ContextVar

from app.core.auth import AuthContext

_mcp_actor: ContextVar[AuthContext | None] = ContextVar("mcp_actor", default=None)


def set_mcp_actor(actor: AuthContext) -> None:
    _mcp_actor.set(actor)


def clear_mcp_actor() -> None:
    _mcp_actor.set(None)


def require_mcp_actor() -> AuthContext:
    actor = _mcp_actor.get()
    if actor is None:
        raise RuntimeError("MCP actor missing")
    return actor
