"""Metering money rates — must stay aligned with catalog pricing (CCR #151)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.billing.plan_pricing import PRO_HOURLY_UNIT_PRICE_USD


def pro_hourly_unit_price_usd() -> Decimal:
    """Pro post-paid hourly rate used when metering charges instance hours."""
    return PRO_HOURLY_UNIT_PRICE_USD
