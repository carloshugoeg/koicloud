"""Resolve the real client IP behind a trusted reverse proxy (Caddy)."""

from __future__ import annotations

from fastapi import Request

from app.core.config import get_settings


def _peer_is_trusted(peer: str | None, trusted: str) -> bool:
    if peer is None:
        return False
    raw = trusted.strip()
    if raw == "*":
        return True
    allowed = {part.strip() for part in raw.split(",") if part.strip()}
    return peer in allowed


def client_ip(request: Request) -> str:
    """Return the client IP for rate limiting.

    When the connecting peer is a trusted proxy, use the leftmost
    ``X-Forwarded-For`` hop (original client). Otherwise use the peer.
    """
    peer = request.client.host if request.client else None
    settings = get_settings()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and _peer_is_trusted(peer, settings.trusted_proxy_ips):
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    return peer or "unknown"
