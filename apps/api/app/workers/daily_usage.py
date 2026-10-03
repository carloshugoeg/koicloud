"""Daily usage aggregation.

Run once (cron or systemd timer), not as a long-lived process:

    cd apps/api && DATABASE_URL=… uv run python -m app.workers.daily_usage

Idempotently upserts ``usage_daily`` from ``pond_samples`` for the previous
UTC day (pass ``USAGE_DAY=YYYY-MM-DD`` to override). Does not invent hosts.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, date, timedelta

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.time import utc_now
from app.modules.metering.service import MeteringService

logger = logging.getLogger(__name__)


def _target_day() -> date:
    override = os.environ.get("USAGE_DAY", "").strip()
    if override:
        return date.fromisoformat(override)
    return utc_now().astimezone(UTC).date() - timedelta(days=1)


async def run(day: date | None = None) -> int:
    target = day or _target_day()
    settings = get_settings()
    async with SessionLocal() as session:
        count = await MeteringService(session, settings).aggregate_day(target)
        await session.commit()
    logger.info("upserted usage_daily for %s pond(s) on %s", count, target.isoformat())
    return count


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    count = asyncio.run(run())
    print(f"usage_daily_upserted={count}")


if __name__ == "__main__":
    main()
