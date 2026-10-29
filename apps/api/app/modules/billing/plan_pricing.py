"""Catalog display pricing for GET /plans (CCR #151 / issue #96 amendment r4)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Protocol

BillingModel = Literal["monthly", "hourly"]
CurrencyCode = Literal["USD"]

# Single Pro hourly catalog rate — shared by GET /plans and metering (CCR #151).
# Kept out of price_monthly_usd so Pro subscribe invoices stay at $0 on signup.
PRO_HOURLY_UNIT_PRICE_USD = Decimal("0.02")
DEFAULT_CURRENCY: CurrencyCode = "USD"
_UNIT_PRICE_QUANT = Decimal("0.0001")


class PlanPricingSource(Protocol):
    postpaid: bool
    price_monthly_usd: Decimal | float | int


def quantize_unit_price(value: Decimal | float | int) -> float:
    """Round money to 4 decimal places for PlanOut.unit_price."""
    quantized = Decimal(str(value)).quantize(_UNIT_PRICE_QUANT, rounding=ROUND_HALF_UP)
    return float(quantized)


def plan_display_pricing(plan: PlanPricingSource) -> tuple[BillingModel, float, CurrencyCode]:
    """Return (billing_model, unit_price, currency) for catalog display."""
    if plan.postpaid:
        raw = PRO_HOURLY_UNIT_PRICE_USD
        return ("hourly", quantize_unit_price(raw), DEFAULT_CURRENCY)
    return ("monthly", quantize_unit_price(plan.price_monthly_usd), DEFAULT_CURRENCY)
