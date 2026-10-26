"""Catalog display pricing for GET /plans (issue #96 pricing amendment)."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Protocol

BillingModel = Literal["monthly", "hourly"]

# Product catalog rate for post-paid (Pro) plans. Kept here — not in
# price_monthly_usd — so subscribe invoices for Pro stay at $0 on signup.
PRO_HOURLY_UNIT_PRICE_USD = Decimal("0.02")
DEFAULT_CURRENCY = "USD"


class PlanPricingSource(Protocol):
    postpaid: bool
    price_monthly_usd: Decimal | float | int


def plan_display_pricing(plan: PlanPricingSource) -> tuple[BillingModel, float, str]:
    """Return (billing_model, unit_price, currency) for catalog display."""
    if plan.postpaid:
        return ("hourly", float(PRO_HOURLY_UNIT_PRICE_USD), DEFAULT_CURRENCY)
    return ("monthly", float(plan.price_monthly_usd), DEFAULT_CURRENCY)
