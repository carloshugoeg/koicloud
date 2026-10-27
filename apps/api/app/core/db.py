from __future__ import annotations

import re
from collections.abc import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_schema() -> str:
    schema = settings.koi_db_schema.strip()
    if not schema:
        return ""
    if not _SCHEMA_RE.fullmatch(schema):
        raise ValueError(f"invalid KOI_DB_SCHEMA={schema!r}")
    return schema


_schema = _safe_schema()
_connect_args: dict[str, object] = {}
if _schema:
    _connect_args["server_settings"] = {"search_path": _schema}

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    future=True,
    echo=False,
    poolclass=NullPool,
    connect_args=_connect_args,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


if _schema:

    @event.listens_for(engine.sync_engine, "connect")
    def _set_search_path(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]  # DBAPI connection
        cursor.execute(f"SET search_path TO {_schema}, public")
        cursor.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        if _schema:
            await session.execute(text(f"SET search_path TO {_schema}, public"))
        yield session
