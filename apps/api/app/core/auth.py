from __future__ import annotations

import base64
import binascii
from typing import Annotated

import jwt
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.base import SchemaModel
from app.core.config import get_settings
from app.core.deps import get_surface
from app.core.enums import AppSurface, UserRole, UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


class AuthContext(SchemaModel):
    user_id: str
    email: str
    role: UserRole
    status: UserStatus
    surface: AppSurface


class NodeContext(SchemaModel):
    node_id: str
    surface: AppSurface = AppSurface.INTERNAL


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    surface: Annotated[AppSurface, Depends(get_surface)],
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(ErrorCode.TOKEN_INVALID)

    try:
        claims = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise AppError(ErrorCode.TOKEN_EXPIRED) from exc
    except jwt.PyJWTError as exc:
        raise AppError(ErrorCode.TOKEN_INVALID) from exc

    if claims.get("token_type") != "access":
        raise AppError(ErrorCode.TOKEN_INVALID)

    return AuthContext(
        user_id=str(claims["sub"]),
        email=str(claims["email"]),
        role=UserRole(str(claims.get("role", UserRole.CLIENT.value))),
        status=UserStatus.ACTIVE,
        surface=surface,
    )


async def get_admin_user(
    user: Annotated[AuthContext, Depends(get_current_user)],
) -> AuthContext:
    if user.role != UserRole.ADMIN:
        raise AppError(ErrorCode.ADMIN_ONLY)
    return user


async def get_node_identity(
    x_node_token: str | None = Header(default=None, alias="X-Node-Token"),
) -> NodeContext:
    settings = get_settings()
    if x_node_token != settings.node_token:
        raise AppError(ErrorCode.TOKEN_INVALID)
    return NodeContext(node_id=settings.node_id)


async def get_mcp_user(
    authorization: str | None = Header(default=None),
    x_koi_agent_password: str | None = Header(default=None, alias="X-KOI-Agent-Password"),
) -> AuthContext:
    settings = get_settings()
    if not settings.mcp_enabled:
        raise AppError(ErrorCode.AGENT_DISABLED)

    slug = settings.mcp_demo_slug
    password = x_koi_agent_password

    if authorization and authorization.lower().startswith("basic "):
        token = authorization.split(" ", 1)[1]
        try:
            decoded = base64.b64decode(token).decode("utf-8")
            slug, password = decoded.split(":", 1)
        except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS) from exc

    if slug != settings.mcp_demo_slug or password != settings.mcp_demo_password:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

    return AuthContext(
        user_id="00000000-0000-0000-0000-000000000001",
        email="agent@koicloud.dev",
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.MCP,
    )
