from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

from app.modules.notifications.templates import RenderedEmail, render_template

logger = logging.getLogger("koicloud.notifications")


class NotificationResult:
    """Represents a successfully sent notification, compatible with both sync and async callers."""

    def __init__(
        self,
        *,
        template: str,
        to: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        self.template = template
        self.to = to
        self.subject = subject
        self.text_body = text_body
        self.html_body = html_body

    def __repr__(self) -> str:
        return f"<NotificationResult template={self.template!r} to={self.to!r} subject={self.subject!r}>"

    def __await__(self) -> Generator[Any, None, NotificationResult]:
        async def _identity() -> NotificationResult:
            return self

        return _identity().__await__()


class ConsoleNotificationProvider:
    """Console provider that logs and prints full email notification details."""

    @staticmethod
    def send(rendered: RenderedEmail, to: str) -> NotificationResult:
        banner = f"=== [NOTIFICATION CONSOLE: {rendered.template}] ==="
        divider = "=" * len(banner)
        output = (
            f"\n{banner}\n"
            f"To: {to}\n"
            f"Subject: {rendered.subject}\n"
            f"--- Text Body ---\n"
            f"{rendered.text_body}\n"
            f"--- HTML Body ---\n"
            f"{rendered.html_body}\n"
            f"{divider}\n"
        )
        # Print to stdout so it is immediately visible in console logs
        print(output)
        logger.info(
            "Notification sent via console: template=%s to=%s subject=%s",
            rendered.template,
            to,
            rendered.subject,
        )
        return NotificationResult(
            template=rendered.template,
            to=to,
            subject=rendered.subject,
            text_body=rendered.text_body,
            html_body=rendered.html_body,
        )


def send(template: str, to: str, context: dict[str, Any]) -> NotificationResult:
    """Validate context, render email, and dispatch via the console provider.

    Rejects unknown templates or incomplete context with ValueError.
    Supports both sync (`res = send(...)`) and async (`res = await send(...)`) invocation.
    """
    if not to or not str(to).strip():
        raise ValueError("Recipient 'to' must be a non-empty email address string.")

    rendered = render_template(template, context)
    return ConsoleNotificationProvider.send(rendered, to.strip())
