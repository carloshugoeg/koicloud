from __future__ import annotations

from uuid import UUID

from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.pond_tokens import PondTokenService
from app.schemas import (
    PondTempAccessCreateRequest,
    PondTempAccessListResponse,
    PondTempAccessOut,
    PondTempAccessSecretOut,
)


async def create_pond_temp_access(
    actor: AuthContext,
    pond_id: UUID,
    payload: PondTempAccessCreateRequest,
) -> PondTempAccessSecretOut:
    async with SessionLocal() as session:
        secret = await PondTokenService(session, get_settings()).create(
            actor,
            pond_id,
            expires_at=payload.expires_at,
            scopes=payload.scopes,
        )
        await session.commit()
        return secret


async def list_pond_temp_access(
    actor: AuthContext,
    pond_id: UUID,
) -> PondTempAccessListResponse:
    async with SessionLocal() as session:
        return await PondTokenService(session, get_settings()).list_for_pond(actor, pond_id)


async def revoke_pond_temp_access(
    actor: AuthContext,
    pond_id: UUID,
    token_id: UUID,
) -> PondTempAccessOut:
    async with SessionLocal() as session:
        out = await PondTokenService(session, get_settings()).revoke(actor, pond_id, token_id)
        await session.commit()
        return out
