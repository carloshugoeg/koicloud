from __future__ import annotations

from app.modules.notifications.service import NotificationResult, send
from app.modules.notifications.templates import TEMPLATES, RenderedEmail, render_template

__all__ = [
    "NotificationResult",
    "RenderedEmail",
    "TEMPLATES",
    "render_template",
    "send",
]
