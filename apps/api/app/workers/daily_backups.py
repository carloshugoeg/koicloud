"""Daily backup scheduler.

Run once (cron or systemd timer), not as a long-lived process:

    cd apps/api && DATABASE_URL=… uv run python -m app.workers.daily_backups

Enqueues ``backup_pond`` jobs with ``kind=daily`` for every running pond that
has no active job. Does not invent hosts — only uses ponds already in the DB.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.backups.service import BackupService

logger = logging.getLogger(__name__)


async def run() -> int:
    settings = get_settings()
    async with SessionLocal() as session:
        jobs = await BackupService(session, settings).enqueue_daily_for_running()
        await session.commit()
    logger.info("enqueued %s daily backup job(s)", len(jobs))
    return len(jobs)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    count = asyncio.run(run())
    print(f"queued={count}")


if __name__ == "__main__":
    main()
