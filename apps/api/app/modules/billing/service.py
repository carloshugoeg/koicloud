from __future__ import annotations

from app.commands import billing as billing_commands
from app.schemas import PlanListResponse


class BillingService:
    """Service encapsulating billing and plans operations for W3."""

    @staticmethod
    async def list_plans() -> PlanListResponse:
        return await billing_commands.list_plans()
