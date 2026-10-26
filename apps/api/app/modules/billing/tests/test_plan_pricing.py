"""Unit tests for catalog display pricing (issue #96 amendment)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.modules.billing.plan_pricing import plan_display_pricing


def test_plan_display_pricing_monthly_uses_price_monthly_usd() -> None:
    plan = SimpleNamespace(postpaid=False, price_monthly_usd=Decimal("5.00"))
    billing_model, unit_price, currency = plan_display_pricing(plan)
    assert billing_model == "monthly"
    assert unit_price == 5.0
    assert currency == "USD"


def test_plan_display_pricing_hourly_uses_pro_catalog_rate() -> None:
    plan = SimpleNamespace(postpaid=True, price_monthly_usd=Decimal("0.00"))
    billing_model, unit_price, currency = plan_display_pricing(plan)
    assert billing_model == "hourly"
    assert unit_price == 0.02
    assert currency == "USD"


def test_plan_display_pricing_sandbox_zero() -> None:
    plan = SimpleNamespace(postpaid=False, price_monthly_usd=Decimal("0.00"))
    billing_model, unit_price, currency = plan_display_pricing(plan)
    assert billing_model == "monthly"
    assert unit_price == 0.0
    assert currency == "USD"
