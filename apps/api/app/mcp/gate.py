from __future__ import annotations

import base64
import binascii

from fastapi import Header, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse

from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface, UserRole, UserStatus
from app.core.errors import ERROR_CATALOG, AppError, ErrorCode
from app.core.models import User
from app.mcp.context import set_mcp_actor
from app.modules.agent_access.service import AgentAccessService


def _parse_basic(authorization: str | None) -> tuple[str | None, str | None]:
    if not authorization or not authorization.lower().startswith("basic "):
        return None, None
    token = authorization.split(" ", 1)[1]
    try:
        decoded = base64.b64decode(token).decode("utf-8")
        slug, password = decoded.split(":", 1)
        return slug, password
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS) from exc


async def _ensure_demo_agent_access(session, settings) -> None:
    """Bootstrap demo slug/password into agent_access when the demo user exists."""
    from sqlalchemy import select

    user = (
        await session.execute(select(User).where(User.email == "demo@koicloud.dev"))
    ).scalar_one_or_none()
    if user is None:
        return
    service = AgentAccessService(session, settings)
    existing = await service.get_row_by_slug(settings.mcp_demo_slug)
    if existing is not None:
        return
    owned = await service.get_row_for_user(user.id)
    if owned is not None:
        return
    await service.ensure_for_user(
        user.id,
        slug=settings.mcp_demo_slug,
        password=settings.mcp_demo_password,
        enabled=True,
    )
    await session.commit()


async def authenticate_mcp(
    *,
    authorization: str | None,
    agent_password: str | None,
) -> AuthContext:
    settings = get_settings()
    if not settings.mcp_enabled:
        raise AppError(ErrorCode.AGENT_DISABLED)

    slug, password = _parse_basic(authorization)
    if password is None:
        password = agent_password
        slug = slug or settings.mcp_demo_slug
    if not slug or not password:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

    async with SessionLocal() as session:
        await _ensure_demo_agent_access(session, settings)
        service = AgentAccessService(session, settings)
        user = await service.authenticate(slug, password)
        if user.status != UserStatus.ACTIVE:
            raise AppError(ErrorCode.AGENT_DISABLED)
        actor = AuthContext(
            user_id=str(user.id),
            email=user.email,
            role=user.role if isinstance(user.role, UserRole) else UserRole(str(user.role)),
            status=UserStatus.ACTIVE,
            surface=AppSurface.MCP,
        )

    set_mcp_actor(actor)
    return actor


async def mcp_gate_dependency(
    request: Request,
    authorization: str | None = Header(default=None),
    x_koi_agent_password: str | None = Header(default=None, alias="X-KOI-Agent-Password"),
) -> AuthContext:
    _ = request
    return await authenticate_mcp(authorization=authorization, agent_password=x_koi_agent_password)


class McpGateMiddleware(BaseHTTPMiddleware):
    """ASGI gate for the Streamable HTTP mount (same credentials as OpenAPI /mcp)."""

    async def dispatch(self, request: StarletteRequest, call_next):
        try:
            actor = await authenticate_mcp(
                authorization=request.headers.get("authorization"),
                agent_password=request.headers.get("x-koi-agent-password"),
            )
        except AppError as exc:
            spec = ERROR_CATALOG[exc.code]
            return JSONResponse(
                status_code=spec.http_status,
                content={
                    "code": exc.code.value,
                    "message": spec.message,
                    "request_id": request.headers.get("x-request-id"),
                },
            )
        request.state.mcp_actor = actor
        set_mcp_actor(actor)
        return await call_next(request)
