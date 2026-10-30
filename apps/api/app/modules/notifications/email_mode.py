from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import SecretStr

from app.core.config import Settings
from app.modules.notifications.errors import EmailConfigurationError


@dataclass(frozen=True, slots=True)
class ConsoleMode:
    kind: Literal["console"] = "console"


@dataclass(frozen=True, slots=True)
class ResendMode:
    from_address: str
    api_key: SecretStr
    kind: Literal["resend"] = "resend"


EmailMode = ConsoleMode | ResendMode


def parse_email_mode(settings: Settings) -> EmailMode:
    """Turn raw settings into one mail mode. Fail only here, not in Settings."""
    provider = settings.email_provider.strip().lower()
    if provider in ("", "console"):
        return ConsoleMode()
    if provider != "resend":
        raise EmailConfigurationError("EMAIL_PROVIDER must be 'console' or 'resend'.")

    api_key = settings.resend_api_key.strip()
    from_address = settings.email_from.strip()
    if not api_key or not from_address:
        raise EmailConfigurationError(
            "EMAIL_PROVIDER=resend requires RESEND_API_KEY and EMAIL_FROM."
        )
    return ResendMode(from_address=from_address, api_key=SecretStr(api_key))
