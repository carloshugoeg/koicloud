from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PondSample


async def latest_sample_size_by_pond(
    session: AsyncSession, pond_ids: Sequence[UUID]
) -> dict[UUID, int]:
    if not pond_ids:
        return {}
    rows = (
        await session.execute(
            select(PondSample.pond_id, PondSample.size_bytes)
            .where(PondSample.pond_id.in_(list(pond_ids)))
            .distinct(PondSample.pond_id)
            .order_by(PondSample.pond_id, PondSample.sampled_at.desc(), PondSample.id.desc())
        )
    ).all()
    return {pond_id: int(size_bytes) for pond_id, size_bytes in rows}
