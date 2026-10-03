from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.config import Settings
from app.core.models import Pond, PondSample, UsageDaily
from app.core.time import utc_now
from app.schemas import (
    HeartbeatSample,
    NodeSampleUpload,
    UsagePondItem,
    UsageResponse,
)

BYTES_PER_GB = Decimal(1024**3)
ZERO = Decimal("0.0000")


def _parse_month(month: str | None, *, now: datetime) -> tuple[str, date, date]:
    """Return (YYYY-MM, first_day, day_after_month)."""
    if month and len(month) == 7 and month[4] == "-":
        try:
            year = int(month[:4])
            mon = int(month[5:7])
            start = date(year, mon, 1)
        except ValueError:
            start = date(now.year, now.month, 1)
    else:
        start = date(now.year, now.month, 1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return f"{start.year:04d}-{start.month:02d}", start, end


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


def compute_day_metrics(
    samples: list[PondSample],
    *,
    day: date,
    now: datetime | None = None,
) -> tuple[Decimal, Decimal]:
    """Aggregate one pond's samples for a calendar day.

    ``instance_hours`` sums intervals where the pond is treated as running.
    Gaps before the first sample (agent down / not yet reporting) count as
    running so control-plane outages do not under-report for the user.
    Intervals between samples use the prior sample's ``container_state``.
    ``storage_gb_hours`` is the mean ``size_bytes`` for the day × 24h / GiB.
    """
    if not samples:
        return ZERO, ZERO

    now = now or utc_now()
    day_start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    window_end = min(day_end, now) if now.astimezone(UTC).date() == day else day_end
    if window_end <= day_start:
        return ZERO, ZERO

    ordered = sorted(samples, key=lambda row: row.sampled_at)
    avg_bytes = sum(int(row.size_bytes) for row in ordered) / len(ordered)
    storage = _quantize(Decimal(str(avg_bytes)) / BYTES_PER_GB * Decimal(24))

    hours = Decimal("0")
    prev_t = day_start
    prev_running = True  # missing leading window → running
    for row in ordered:
        sampled_at = row.sampled_at
        if sampled_at.tzinfo is None:
            sampled_at = sampled_at.replace(tzinfo=UTC)
        else:
            sampled_at = sampled_at.astimezone(UTC)
        if sampled_at < day_start:
            prev_running = row.container_state == "running"
            continue
        if sampled_at > window_end:
            break
        delta = Decimal(str((sampled_at - prev_t).total_seconds())) / Decimal(3600)
        if prev_running and delta > 0:
            hours += delta
        prev_t = sampled_at
        prev_running = row.container_state == "running"

    tail = Decimal(str((window_end - prev_t).total_seconds())) / Decimal(3600)
    if prev_running and tail > 0:
        hours += tail

    return _quantize(hours), storage


class MeteringService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def ingest_samples(self, samples: list[NodeSampleUpload]) -> int:
        if not samples:
            return 0
        now = utc_now()
        written = 0
        for sample in samples:
            pond = await self.session.get(Pond, sample.pond_id)
            if pond is None:
                continue
            self.session.add(
                PondSample(
                    pond_id=pond.id,
                    size_bytes=int(sample.size_bytes),
                    container_state=sample.container_state,
                    sampled_at=now,
                )
            )
            written += 1
        if written:
            await self.session.flush()
        return written

    async def ingest_heartbeat_samples(self, samples: list[HeartbeatSample]) -> int:
        if not samples:
            return 0
        now = utc_now()
        written = 0
        for sample in samples:
            pond_id = await self._resolve_pond_id(sample.pond_name)
            if pond_id is None:
                continue
            self.session.add(
                PondSample(
                    pond_id=pond_id,
                    size_bytes=int(sample.size_bytes),
                    container_state=sample.container_state,
                    sampled_at=now,
                )
            )
            written += 1
        if written:
            await self.session.flush()
        return written

    async def aggregate_day(self, day: date | None = None) -> int:
        """Idempotently upsert ``usage_daily`` for every pond with samples that day."""
        target = day or (utc_now().astimezone(UTC).date() - timedelta(days=1))
        day_start = datetime(target.year, target.month, target.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        pond_ids = (
            await self.session.execute(
                select(PondSample.pond_id)
                .where(
                    PondSample.sampled_at >= day_start,
                    PondSample.sampled_at < day_end,
                )
                .distinct()
            )
        ).scalars().all()

        upserted = 0
        for pond_id in pond_ids:
            rows = (
                await self.session.execute(
                    select(PondSample)
                    .where(
                        PondSample.pond_id == pond_id,
                        PondSample.sampled_at >= day_start,
                        PondSample.sampled_at < day_end,
                    )
                    .order_by(PondSample.sampled_at.asc())
                )
            ).scalars().all()
            instance_hours, storage_gb_hours = compute_day_metrics(
                list(rows), day=target, now=utc_now()
            )
            stmt = insert(UsageDaily).values(
                pond_id=pond_id,
                day=target,
                instance_hours=instance_hours,
                storage_gb_hours=storage_gb_hours,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="usage_daily_pk",
                set_={
                    "instance_hours": stmt.excluded.instance_hours,
                    "storage_gb_hours": stmt.excluded.storage_gb_hours,
                },
            )
            await self.session.execute(stmt)
            upserted += 1

        if upserted:
            await self.session.flush()
        return upserted

    async def get_usage(self, actor: AuthContext, month: str | None = None) -> UsageResponse:
        now = utc_now()
        month_label, start, end = _parse_month(month, now=now)

        stmt: Select[tuple[UUID, str, Decimal, Decimal]] = (
            select(
                Pond.id,
                Pond.name,
                func.coalesce(func.sum(UsageDaily.instance_hours), 0),
                func.coalesce(func.sum(UsageDaily.storage_gb_hours), 0),
            )
            .join(UsageDaily, UsageDaily.pond_id == Pond.id)
            .where(
                Pond.user_id == actor.user_id,
                UsageDaily.day >= start,
                UsageDaily.day < end,
            )
            .group_by(Pond.id, Pond.name)
            .order_by(Pond.name.asc())
        )
        rows = (await self.session.execute(stmt)).all()

        ponds: list[UsagePondItem] = []
        total_instance = Decimal("0")
        total_storage = Decimal("0")
        for pond_id, pond_name, instance_hours, storage_gb_hours in rows:
            ih = _quantize(Decimal(str(instance_hours)))
            sh = _quantize(Decimal(str(storage_gb_hours)))
            if ih == 0 and sh == 0:
                continue
            total_instance += ih
            total_storage += sh
            ponds.append(
                UsagePondItem(
                    pond_id=pond_id,
                    pond_name=pond_name,
                    instance_hours=float(ih),
                    storage_gb_hours=float(sh),
                )
            )

        return UsageResponse(
            month=month_label,
            total_instance_hours=float(_quantize(total_instance)),
            total_storage_gb_hours=float(_quantize(total_storage)),
            ponds=ponds,
        )

    async def _resolve_pond_id(self, pond_name: str) -> UUID | None:
        name = pond_name.strip()
        if not name:
            return None
        rows = (
            await self.session.execute(
                select(Pond.id).where(
                    Pond.name == name,
                    Pond.node_id == self.settings.node_id,
                )
            )
        ).scalars().all()
        if len(rows) != 1:
            return None
        return rows[0]
