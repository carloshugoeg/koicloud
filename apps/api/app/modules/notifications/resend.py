from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from typing import Protocol

import httpx

from app.modules.notifications.email_mode import ResendMode
from app.modules.notifications.errors import NotificationDeliveryError
from app.modules.notifications.templates import RenderedEmail

logger = logging.getLogger("koicloud.notifications")

RESEND_URL = "https://api.resend.com/emails"
MAX_ATTEMPTS = 2
REQUEST_TIMEOUT_SECONDS = 10.0


class PostFn(Protocol):
    def __call__(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, object],
        timeout: float,
    ) -> httpx.Response: ...


def default_post(
    url: str,
    *,
    headers: Mapping[str, str],
    json: Mapping[str, object],
    timeout: float,
) -> httpx.Response:
    return httpx.post(url, headers=headers, json=dict(json), timeout=timeout)


def deliver_via_resend(
    mode: ResendMode,
    rendered: RenderedEmail,
    to: str,
    post: PostFn,
) -> None:
    secret = mode.api_key.get_secret_value()
    headers = {
        "Authorization": f"Bearer {secret}",
        "Idempotency-Key": str(uuid.uuid4()),
    }
    payload: dict[str, object] = {
        "from": mode.from_address,
        "to": [to],
        "subject": rendered.subject,
        "html": rendered.html_body,
        "text": rendered.text_body,
    }
    for _attempt in range(MAX_ATTEMPTS):
        try:
            response = post(
                RESEND_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.TransportError:
            continue
        if response.is_success:
            return
    _raise_delivery_error(rendered.template, to, secret)


def _redact(value: str, secret: str) -> str:
    if not secret:
        return value
    return value.replace(secret, "[redacted]")


def _raise_delivery_error(template: str, to: str, secret: str) -> None:
    safe_template = _redact(template, secret)
    safe_to = _redact(to, secret)
    logger.error(
        "Resend delivery failed template=%s to=%s",
        safe_template,
        safe_to,
    )
    raise NotificationDeliveryError(
        f"Resend delivery failed template={safe_template} to={safe_to}"
    )
