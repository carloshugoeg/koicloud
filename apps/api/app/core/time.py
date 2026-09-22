from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def plus_seconds(seconds: int) -> datetime:
    return utc_now() + timedelta(seconds=seconds)


def plus_days(days: int) -> datetime:
    return utc_now() + timedelta(days=days)
