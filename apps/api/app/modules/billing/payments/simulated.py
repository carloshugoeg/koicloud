from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.enums import PaymentStatus
from app.core.models import Invoice
from app.modules.billing.checks import CardInput, card_declined
from app.modules.billing.payments.port import PaymentAttempt


class SimulatedPaymentProvider:
    """Demo adapter: a valid card succeeds in the same request. An invalid card declines."""

    def start_payment(self, invoice: Invoice, card: CardInput | None = None) -> PaymentAttempt:
        if card is not None and card_declined(card):
            return PaymentAttempt(
                status=PaymentStatus.FAILED,
                provider="simulated",
                provider_ref=f"sim_declined_{uuid4().hex[:8]}",
                checkout_url=None,
            )
        return PaymentAttempt(
            status=PaymentStatus.SUCCEEDED,
            provider="simulated",
            provider_ref=f"sim_{invoice.id}_{uuid4().hex[:8]}",
            checkout_url=None,
        )

    def parse_confirmation(self, raw: Any) -> str:
        if isinstance(raw, dict) and "provider_ref" in raw:
            return str(raw["provider_ref"])
        return str(raw)
