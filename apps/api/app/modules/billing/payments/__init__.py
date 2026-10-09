from __future__ import annotations

from app.core.config import Settings
from app.modules.billing.payments.port import PaymentAttempt, PaymentProvider
from app.modules.billing.payments.simulated import SimulatedPaymentProvider


def get_payment_provider(settings: Settings) -> PaymentProvider:
    name = (settings.payment_provider or "simulated").strip().lower()
    if name == "simulated":
        return SimulatedPaymentProvider()
    raise ValueError(f"unsupported PAYMENT_PROVIDER={settings.payment_provider!r}")


__all__ = [
    "PaymentAttempt",
    "PaymentProvider",
    "SimulatedPaymentProvider",
    "get_payment_provider",
]
