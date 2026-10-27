"""Simple per-process sliding-window rate limiter (slowapi stand-in for v0)."""

from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from app.core.errors import AppError, ErrorCode

_windows: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, *, limit: int, window_seconds: float = 60.0) -> None:
    """Raise ``rate_limited`` when ``key`` exceeds ``limit`` hits in the window."""
    now = monotonic()
    bucket = _windows[key]
    while bucket and now - bucket[0] >= window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise AppError(ErrorCode.RATE_LIMITED)
    bucket.append(now)


def reset_rate_limits() -> None:
    """Clear all windows (tests only)."""
    _windows.clear()
