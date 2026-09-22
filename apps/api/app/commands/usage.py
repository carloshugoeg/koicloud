from __future__ import annotations

from app.core.auth import AuthContext
from app.schemas import UsageResponse


async def get_usage(_: AuthContext, month: str | None = None) -> UsageResponse:
    usage = UsageResponse.example()
    if month:
        usage.month = month
    return usage
