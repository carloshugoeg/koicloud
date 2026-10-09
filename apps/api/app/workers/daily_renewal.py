"""Daily subscription renewal (E2-04 / G2).

Run once (cron or systemd timer), not as a long-lived process:

    cd apps/api && DATABASE_URL=… uv run python -m app.workers.daily_renewal

For each active subscription past ``current_period_end``:
- ``cancel_at_period_end`` → status ``canceled``
- otherwise → ``BillingService.renew`` (next invoice through the payment port)

Does not invent a parallel payment path. Future provider-managed renewals can be
skipped here once an adapter marks them; simulated always renews in-process.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import SubscriptionStatus
from app.core.models import Subscription
from app.core.time import utc_now
from app.modules.billing.payments import get_payment_provider
from app.modules.billing.service import BillingService

logger = logging.getLogger(__name__)

ADVISORY_LOCK_KEY = 2_040_930


@dataclass(frozen=True)
class RenewalStats:
    closed: int = 0
    renewed: int = 0
    skipped_lock: bool = False


async def _try_lock(session: AsyncSession) -> bool:
    result = await session.execute(
        text("SELECT pg_try_advisory_lock(CAST(:key AS bigint))"),
        {"key": ADVISORY_LOCK_KEY},
    )
    return bool(result.scalar_one())


async def _release_lock(session: AsyncSession) -> None:
    await session.execute(
        text("SELECT pg_advisory_unlock(CAST(:key AS bigint))"),
        {"key": ADVISORY_LOCK_KEY},
    )


async def tick(session: AsyncSession) -> RenewalStats:
    if not await _try_lock(session):
        return RenewalStats(skipped_lock=True)
    try:
        settings = get_settings()
        provider = get_payment_provider(settings)
        billing = BillingService(session, settings, provider)
        now = utc_now()
        due = (
            await session.scalars(
                select(Subscription)
                .where(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.current_period_end <= now,
                )
                .order_by(Subscription.current_period_end.asc())
            )
        ).all()

        closed = 0
        renewed = 0
        for subscription in due:
            if subscription.cancel_at_period_end:
                subscription.status = SubscriptionStatus.CANCELED
                closed += 1
                continue
            await billing.renew(subscription)
            renewed += 1

        await session.commit()
        return RenewalStats(closed=closed, renewed=renewed)
    except Exception:
        await session.rollback()
        raise
    finally:
        try:
            await _release_lock(session)
        except Exception:
            logger.exception("daily_renewal advisory unlock failed")


async def run() -> RenewalStats:
    async with SessionLocal() as session:
        return await tick(session)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    stats = asyncio.run(run())
    logger.info(
        "renewal closed=%s renewed=%s skipped_lock=%s",
        stats.closed,
        stats.renewed,
        stats.skipped_lock,
    )
    print(f"closed={stats.closed} renewed={stats.renewed}")


if __name__ == "__main__":
    main()
