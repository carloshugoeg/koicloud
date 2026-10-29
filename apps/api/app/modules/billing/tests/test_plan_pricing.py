"""Unit tests for catalog display pricing (CCR #151)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.modules.billing.plan_pricing import (
    PRO_HOURLY_UNIT_PRICE_USD,
    plan_display_pricing,
    quantize_unit_price,
)
from app.modules.metering.rates import pro_hourly_unit_price_usd


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


def test_quantize_unit_price_four_decimals() -> None:
    assert quantize_unit_price(Decimal("0.02")) == 0.02
    assert quantize_unit_price(Decimal("0.02004")) == 0.02
    assert quantize_unit_price(Decimal("0.02005")) == 0.0201
    assert quantize_unit_price(5) == 5.0


def test_pro_hourly_rate_shared_with_metering() -> None:
    """Parity: GET /plans Pro rate is the same object metering imports."""
    assert pro_hourly_unit_price_usd() is PRO_HOURLY_UNIT_PRICE_USD
    assert pro_hourly_unit_price_usd() == Decimal("0.02")
    plan = SimpleNamespace(postpaid=True, price_monthly_usd=Decimal("0"))
    _, unit_price, currency = plan_display_pricing(plan)
    assert unit_price == float(pro_hourly_unit_price_usd())
    assert currency == "USD"
