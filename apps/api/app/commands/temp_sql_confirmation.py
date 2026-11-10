"""Internal helpers for pond-temp SQL confirmation binding (CCR TEMP-CONFIRM).

No client API. Used by confirmations.py and sql.py.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.config import Settings, get_settings
from app.core.enums import UserStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import Pond, PondToken, User
from app.core.time import utc_now
from app.modules.pond_tokens.service import TEMP_ACCESS_TOOLS, phase_of

if TYPE_CHECKING:
    from app.schemas import RunSQLRequest


@dataclass(frozen=True, slots=True)
class TempSqlDispatchGrant:
    """Non-client-constructible proof that a temp confirmation was claimed."""

    confirmation_id: UUID
    pond_token_id: UUID
    pond_id: UUID
    action: str
    request_digest: str
    query: str
    mode: str


def canonical_temp_sql_digest(
    *,
    pond_token_id: UUID | str,
    pond_id: UUID | str,
    query: str,
) -> str:
    envelope = {
        "v": 1,
        "pond_token_id": str(pond_token_id).lower(),
        "pond_id": str(pond_id).lower(),
        "action": "run_sql_write",
        "request": {"query": query, "mode": "write"},
    }
    payload = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def digests_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.lower(), right.lower())


def confirmation_expiry(
    *,
    now: datetime,
    pond_token_expires_at: datetime,
    settings: Settings | None = None,
) -> datetime:
    cfg = settings or get_settings()
    ttl = min(int(cfg.confirm_ttl_seconds), 300)
    candidate = now.replace(microsecond=0) + timedelta(seconds=ttl)
    token_exp = pond_token_expires_at
    if token_exp.tzinfo is None and now.tzinfo is not None:
        token_exp = token_exp.replace(tzinfo=now.tzinfo)
    return min(candidate, token_exp.replace(microsecond=0))


def is_temp_actor(actor: AuthContext) -> bool:
    return actor.pond_token_id is not None


async def lock_live_pond_token(
    session: AsyncSession,
    *,
    pond_token_id: UUID,
    actor: AuthContext,
    now: datetime | None = None,
) -> PondToken:
    """SELECT … FOR UPDATE and revalidate credential against the database."""
    clock = now or utc_now()
    row = (
        await session.execute(
            select(PondToken).where(PondToken.id == pond_token_id).with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
    if phase_of(row, now=clock) in {"expired", "revoked"}:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

    pond = await session.get(Pond, row.pond_id)
    if pond is None:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
    if actor.pond_id is not None and str(pond.id) != actor.pond_id:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
    if str(pond.user_id) != actor.user_id:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

    owner = await session.get(User, pond.user_id)
    if owner is None or owner.status != UserStatus.ACTIVE:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)

    scopes = frozenset(row.scopes or []) & TEMP_ACCESS_TOOLS
    if not scopes:
        scopes = TEMP_ACCESS_TOOLS
    if "run_sql" not in scopes:
        raise AppError(ErrorCode.AGENT_DISABLED)
    return row


def require_temp_write_request(payload: RunSQLRequest) -> None:
    from app.core.enums import SQLMode

    if payload.mode != SQLMode.WRITE:
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)


def grant_from_claim(
    *,
    confirmation_id: UUID,
    pond_token_id: UUID,
    pond_id: UUID,
    request_digest: str,
    query: str,
) -> TempSqlDispatchGrant:
    return TempSqlDispatchGrant(
        confirmation_id=confirmation_id,
        pond_token_id=pond_token_id,
        pond_id=pond_id,
        action="run_sql_write",
        request_digest=request_digest,
        query=query,
        mode="write",
    )


def assert_grant_matches_request(
    grant: TempSqlDispatchGrant,
    *,
    pond_id: UUID,
    query: str,
    mode: str,
) -> None:
    if grant.action != "run_sql_write":
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
    if grant.pond_id != pond_id:
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
    if grant.mode != "write" or mode != "write":
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
    expected = canonical_temp_sql_digest(
        pond_token_id=grant.pond_token_id,
        pond_id=pond_id,
        query=query,
    )
    if not digests_equal(grant.request_digest, expected) or grant.query != query:
        raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
