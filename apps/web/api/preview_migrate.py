"""Upgrade the shared preview database on startup.

Vercel previews are a serverless function. They do not run the container
command that applies Alembic, and deploy.yml is intentionally disabled.
Every cold start converges to head. Revision 0005 only adds a table, so a
preview that does not know about it keeps working on the same database.

Alembic's env.py must not learn the preview schema. The guard lives here,
in PGOPTIONS, for the duration of this process's upgrade.
"""

from __future__ import annotations

import os
from pathlib import Path

_LOCK_KEY = 82460005


def _preview() -> bool:
    return (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview"


def _alembic_root() -> Path:
    here = Path(__file__).resolve().parent
    vendored = here / "_koi_api"
    if (vendored / "alembic.ini").is_file():
        return vendored
    # apps/web/api -> apps/api when the build has not vendored Alembic yet.
    return here.parents[1] / "api"


def _libpq_url(url: str) -> str:
    from app.core.config import to_sync_database_url

    sync = to_sync_database_url(url)
    return sync.replace("postgresql+psycopg://", "postgresql://", 1)


def ensure_preview_migrations() -> None:
    """Apply Alembic head on the preview schema. No-op off Vercel preview."""
    if not _preview():
        return

    from preview_seed import _database_url_looks_like_production

    from app.core.config import get_settings
    from app.core.db import resolve_preview_schema

    unpooled = (os.environ.get("DATABASE_URL_UNPOOLED") or "").strip()
    current = (os.environ.get("DATABASE_URL") or "").strip() or get_settings().database_url
    target = unpooled or current
    if _database_url_looks_like_production(target):
        return

    schema = resolve_preview_schema(
        vercel_env="preview",
        schema=os.environ.get("KOI_DB_SCHEMA") or "",
    )
    if not schema:
        return

    previous_url = os.environ.get("DATABASE_URL")
    previous_options = os.environ.get("PGOPTIONS")
    if unpooled:
        os.environ["DATABASE_URL"] = unpooled
        get_settings.cache_clear()
    os.environ["PGOPTIONS"] = f"-c search_path={schema},public"
    try:
        _upgrade_locked(_libpq_url(target))
    finally:
        if previous_options is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = previous_options
        if unpooled:
            if previous_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_url
            get_settings.cache_clear()


def _upgrade_locked(url: str) -> None:
    import psycopg
    from alembic.config import Config

    from alembic import command

    root = _alembic_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    # Session lock: a second cold start waits, then finds head and stops.
    with psycopg.connect(url) as connection:
        connection.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            command.upgrade(config, "head")
        finally:
            connection.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))
