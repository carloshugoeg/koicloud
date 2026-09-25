from __future__ import annotations

from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url


def reset_pond_tables() -> None:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM jobs"))
        connection.execute(text("DELETE FROM pond_status"))
        connection.execute(text("DELETE FROM ponds"))
        connection.execute(text("DELETE FROM subscriptions"))
        connection.execute(text("DELETE FROM users"))
        connection.execute(text("DELETE FROM nodes"))
    engine.dispose()
