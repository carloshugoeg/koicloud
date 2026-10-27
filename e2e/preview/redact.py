"""Strip credential material before it reaches a log or a results file."""

from __future__ import annotations

import json
import re
from pathlib import Path

_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_CONF = re.compile(r"\bconf_[A-Za-z0-9_-]{4,}\b")
_SECRET_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "authorization",
}


def redact(text: str, secrets: list[str] | None = None) -> str:
    cleaned = text
    for secret in secrets or []:
        if len(secret) >= 4:
            cleaned = cleaned.replace(secret, "[redacted]")
    cleaned = _JWT.sub("[redacted]", cleaned)
    cleaned = _BEARER.sub("[redacted]", cleaned)
    cleaned = _CONF.sub("[redacted]", cleaned)
    return cleaned


def secret_values(path: str | None) -> list[str]:
    if not path:
        return []
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    found: list[str] = []
    _walk(payload, found)
    return found


def _walk(node: object, found: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.lower() in _SECRET_KEYS and isinstance(value, str):
                if len(value) >= 4:
                    found.append(value)
            else:
                _walk(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk(item, found)
