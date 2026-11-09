from __future__ import annotations

import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.config import Settings
from app.core.enums import UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import Pond, PondToken, User
from app.core.security import hash_password, verify_password
from app.core.time import utc_now
from app.modules.ponds import PondService
from app.schemas import (
    PondTempAccessListResponse,
    PondTempAccessOut,
    PondTempAccessSecretOut,
)

TEMP_ACCESS_TOOLS: frozenset[str] = frozenset({"whoami", "get_pond", "run_sql"})


def phase_of(row: PondToken, *, now: datetime | None = None) -> str:
    """Derive statechart phase from stored timestamps."""
    clock = now or utc_now()
    if row.revoked_at is not None:
        return "revoked"
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=clock.tzinfo)
    if clock >= expires:
        return "expired"
    return "issued"


def _mcp_url(settings: Settings) -> str:
    return f"https://{settings.koicloud_domain}{settings.mcp_prefix}"


def _new_slug() -> str:
    return f"pond-{secrets.token_urlsafe(9)}"


def _new_password() -> str:
    return secrets.token_urlsafe(18)


class PondTokenService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.ponds = PondService(session, settings)

    def to_out(self, row: PondToken) -> PondTempAccessOut:
        return PondTempAccessOut(
            id=row.id,
            pond_id=row.pond_id,
            slug=row.access_slug,
            url=_mcp_url(self.settings),
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
            scopes=list(row.scopes or []),
            created_at=row.created_at,
        )

    def to_secret(self, row: PondToken, password: str) -> PondTempAccessSecretOut:
        return PondTempAccessSecretOut(
            id=row.id,
            pond_id=row.pond_id,
            slug=row.access_slug,
            url=_mcp_url(self.settings),
            password=password,
            expires_at=row.expires_at,
            scopes=list(row.scopes or []),
        )

    async def create(
        self,
        actor: AuthContext,
        pond_id: UUID,
        *,
        expires_at: datetime,
        scopes: list[str] | None = None,
    ) -> PondTempAccessSecretOut:
        await self.ponds.get_owned(actor, pond_id)
        resolved = list(scopes) if scopes else sorted(TEMP_ACCESS_TOOLS)
        unknown = set(resolved) - TEMP_ACCESS_TOOLS
        if unknown:
            raise AppError(ErrorCode.INTERNAL_ERROR, message="scopes inválidos para acceso temporal")
        password = _new_password()
        row = PondToken(
            pond_id=pond_id,
            access_slug=_new_slug(),
            password_hash=hash_password(password),
            expires_at=expires_at,
            revoked_at=None,
            scopes=resolved,
        )
        self.session.add(row)
        await self.session.flush()
        return self.to_secret(row, password)

    async def list_for_pond(self, actor: AuthContext, pond_id: UUID) -> PondTempAccessListResponse:
        await self.ponds.get_owned(actor, pond_id)
        rows = (
            await self.session.execute(
                select(PondToken)
                .where(PondToken.pond_id == pond_id)
                .order_by(PondToken.created_at.desc())
            )
        ).scalars().all()
        return PondTempAccessListResponse(tokens=[self.to_out(row) for row in rows])

    async def revoke(
        self, actor: AuthContext, pond_id: UUID, token_id: UUID
    ) -> PondTempAccessOut:
        await self.ponds.get_owned(actor, pond_id)
        # Same PondToken row-lock ordering as temp SQL claim/admission.
        row = (
            await self.session.execute(
                select(PondToken).where(PondToken.id == token_id).with_for_update()
            )
        ).scalar_one_or_none()
        if row is None or row.pond_id != pond_id:
            raise AppError(ErrorCode.POND_NOT_FOUND)
        if row.revoked_at is None:
            row.revoked_at = utc_now()
            await self.session.flush()
        return self.to_out(row)

    async def authenticate(
        self, slug: str, password: str
    ) -> tuple[User, Pond, frozenset[str], UUID]:
        """Return owner, pond, effective tools, and PondToken.id (logical session)."""
        row = (
            await self.session.execute(
                select(PondToken).where(PondToken.access_slug == slug)
            )
        ).scalar_one_or_none()
        if row is None or not verify_password(password, row.password_hash):
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
        phase = phase_of(row)
        if phase in {"expired", "revoked"}:
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

        pond = await self.session.get(Pond, row.pond_id)
        if pond is None:
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
        user = await self.session.get(User, pond.user_id)
        if user is None:
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
        # CCR: suspended/invalid owner → 401 at authenticate (temp path).
        if user.status != UserStatus.ACTIVE:
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

        scopes = frozenset(row.scopes or []) & TEMP_ACCESS_TOOLS
        if not scopes:
            scopes = TEMP_ACCESS_TOOLS
        # Derive confirm_action only when run_sql is already granted.
        if "run_sql" in scopes:
            scopes = frozenset(set(scopes) | {"confirm_action"})
        return user, pond, scopes, row.id
