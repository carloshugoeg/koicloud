from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SQLMode
from app.core.models import Base, pg_enum
from app.core.time import utc_now


class SqlHistory(Base):
    __tablename__ = "sql_history"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pond_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ponds.id", ondelete="CASCADE"), nullable=False
    )
    query_truncated: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[SQLMode] = mapped_column(pg_enum(SQLMode, "sql_mode"), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
