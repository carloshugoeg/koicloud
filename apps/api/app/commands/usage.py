from __future__ import annotations

from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.metering.service import MeteringService
from app.schemas import UsageResponse


async def get_usage(actor: AuthContext, month: str | None = None) -> UsageResponse:
    async with SessionLocal() as session:
        return await MeteringService(session, get_settings()).get_usage(actor, month)
