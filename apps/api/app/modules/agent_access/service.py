from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.core.models import AgentAccess, User
from app.core.security import hash_password, verify_password
from app.core.time import utc_now
from app.schemas import AgentAccessOut, AgentAccessSecretOut


def _mcp_url(settings: Settings) -> str:
    return f"https://{settings.koicloud_domain}{settings.mcp_prefix}"


def _new_slug() -> str:
    return f"agent-{secrets.token_urlsafe(9)}"


def _new_password() -> str:
    return secrets.token_urlsafe(18)


class AgentAccessService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def get_row_for_user(self, user_id: UUID) -> AgentAccess | None:
        return (
            await self.session.execute(
                select(AgentAccess).where(AgentAccess.user_id == user_id)
            )
        ).scalar_one_or_none()

    async def get_row_by_slug(self, slug: str) -> AgentAccess | None:
        return (
            await self.session.execute(
                select(AgentAccess).where(AgentAccess.access_slug == slug)
            )
        ).scalar_one_or_none()

    async def ensure_for_user(
        self,
        user_id: UUID,
        *,
        slug: str | None = None,
        password: str | None = None,
        enabled: bool = True,
    ) -> tuple[AgentAccess, str | None]:
        row = await self.get_row_for_user(user_id)
        if row is not None:
            return row, None

        plaintext = password or _new_password()
        row = AgentAccess(
            user_id=user_id,
            access_slug=slug or _new_slug(),
            password_hash=hash_password(plaintext),
            enabled=enabled,
            rotated_at=utc_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row, plaintext

    def to_out(self, row: AgentAccess) -> AgentAccessOut:
        return AgentAccessOut(
            slug=row.access_slug,
            url=_mcp_url(self.settings),
            enabled=row.enabled,
            rotated_at=row.rotated_at,
        )

    def to_secret(self, row: AgentAccess, password: str) -> AgentAccessSecretOut:
        return AgentAccessSecretOut(
            slug=row.access_slug,
            url=_mcp_url(self.settings),
            password=password,
        )

    async def get_or_create_out(self, actor: AuthContext) -> AgentAccessOut:
        row, _plaintext = await self.ensure_for_user(UUID(actor.user_id))
        return self.to_out(row)

    async def rotate(self, actor: AuthContext) -> AgentAccessSecretOut:
        row, _ = await self.ensure_for_user(UUID(actor.user_id))
        password = _new_password()
        row.password_hash = hash_password(password)
        row.rotated_at = utc_now()
        await self.session.flush()
        return self.to_secret(row, password)

    async def toggle(self, actor: AuthContext, *, enabled: bool) -> bool:
        row, _ = await self.ensure_for_user(UUID(actor.user_id))
        row.enabled = enabled
        await self.session.flush()
        return row.enabled

    async def authenticate(self, slug: str, password: str) -> User:
        row = await self.get_row_by_slug(slug)
        if row is None or not verify_password(password, row.password_hash):
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
        if not row.enabled:
            raise AppError(ErrorCode.AGENT_DISABLED)

        user = await self.session.get(User, row.user_id)
        if user is None:
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
        return user
