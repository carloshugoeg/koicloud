from __future__ import annotations


class EmailConfigurationError(Exception):
    """EMAIL_PROVIDER=resend is missing RESEND_API_KEY or EMAIL_FROM."""


class NotificationDeliveryError(Exception):
    """The selected provider could not deliver the message."""
