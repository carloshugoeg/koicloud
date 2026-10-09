from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.enums import PaymentStatus
from app.core.models import Invoice


@dataclass(frozen=True, slots=True)
class PaymentAttempt:
    status: PaymentStatus
    provider: str
    provider_ref: str
    checkout_url: str | None = None


class PaymentProvider(Protocol):
    def start_payment(self, invoice: Invoice) -> PaymentAttempt:
        """Start a payment for an issued invoice."""

    def parse_confirmation(self, raw: Any) -> str:
        """Return provider_ref from a provider confirmation payload."""
