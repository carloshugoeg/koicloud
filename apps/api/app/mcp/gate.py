from __future__ import annotations

import base64
import binascii

from fastapi import Header, Request
from sqlalchemy import select

from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import User
from app.mcp.context import set_mcp_actor

DEMO_AGENT_EMAIL = "demo@koicloud.dev"


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

    if slug != settings.mcp_demo_slug or password != settings.mcp_demo_password:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == DEMO_AGENT_EMAIL))
        ).scalar_one_or_none()

    if user is None:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
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
