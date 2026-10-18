from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.enums import SQLMode
from app.core.time import utc_now
from app.modules.sql_console.models import SqlHistory
from app.schemas import SQLHistoryItem, SQLHistoryResponse

QUERY_MAX_CHARS = 4000


@dataclass(frozen=True, slots=True)
class HistoryCursor:
    executed_at: datetime
    row_id: UUID


@dataclass(frozen=True, slots=True)
class HistoryWrite:
    user_id: UUID
    pond_id: UUID
    query: str
    mode: SQLMode
    row_count: int
    duration_ms: int


def truncate_query(query: str) -> str:
    return query[:QUERY_MAX_CHARS]


def to_item(row: SqlHistory) -> SQLHistoryItem:
    return SQLHistoryItem(
        id=row.id,
        pond_id=row.pond_id,
        query_truncated=row.query_truncated,
        mode=row.mode,
        row_count=row.row_count,
        duration_ms=row.duration_ms,
        executed_at=row.executed_at,
    )


class SqlConsoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(self, entry: HistoryWrite) -> SqlHistory:
        row = SqlHistory(
            user_id=entry.user_id,
            pond_id=entry.pond_id,
            query_truncated=truncate_query(entry.query),
            mode=entry.mode,
            row_count=entry.row_count,
            duration_ms=entry.duration_ms,
            executed_at=utc_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_for_actor(
        self,
        actor: AuthContext,
        pond_id: UUID,
        *,
        limit: int,
        cursor: HistoryCursor | None,
    ) -> SQLHistoryResponse:
        stmt = (
            select(SqlHistory)
            .where(
                SqlHistory.user_id == UUID(actor.user_id),
                SqlHistory.pond_id == pond_id,
            )
            .order_by(SqlHistory.executed_at.desc(), SqlHistory.id.desc())
        )
        if cursor is not None:
            stmt = stmt.where(
                or_(
                    SqlHistory.executed_at < cursor.executed_at,
                    and_(
                        SqlHistory.executed_at == cursor.executed_at,
                        SqlHistory.id < cursor.row_id,
                    ),
                )
            )
        rows = list((await self.session.execute(stmt.limit(limit + 1))).scalars().all())
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page:
            last = page[-1]
            next_cursor = f"{last.executed_at.isoformat()}|{last.id}"
        return SQLHistoryResponse(
            events=[to_item(row) for row in page],
            next_cursor=next_cursor,
        )
