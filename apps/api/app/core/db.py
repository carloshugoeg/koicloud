from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator

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


def resolve_preview_schema(*, vercel_env: str | None, schema: str) -> str:
    """Return a Postgres schema name only for Vercel preview.

    Production / local / CI keep the default search_path (same as main).
    """
    if (vercel_env or "").strip().lower() != "preview":
        return ""
    cleaned = schema.strip()
    if not cleaned:
        return ""
    if not _SCHEMA_RE.fullmatch(cleaned):
        raise ValueError(f"invalid KOI_DB_SCHEMA={schema!r}")
    return cleaned


_schema = resolve_preview_schema(
    vercel_env=os.environ.get("VERCEL_ENV"),
    schema=settings.koi_db_schema,
)
_connect_args: dict[str, object] = {}
if _schema:
    # Preview only: set search_path via libpq server_settings (no per-session SET).
    _connect_args["server_settings"] = {"search_path": f"{_schema}, public"}

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    future=True,
    echo=False,
    poolclass=NullPool,
    connect_args=_connect_args,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
