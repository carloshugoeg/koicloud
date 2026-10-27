from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import get_settings, to_sync_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", to_sync_database_url(settings.database_url))

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    schema = (settings.koi_db_schema or "").strip()
    if schema and not schema.replace("_", "").isalnum():
        raise ValueError(f"invalid KOI_DB_SCHEMA={schema!r}")
    with connectable.connect() as connection:
        if schema:
            # Preview DB isolates KoiCloud tables in a dedicated schema.
            from sqlalchemy import text

            # Schema is provisioned out-of-band for preview DBs; only set path here.
            connection.execute(text(f"SET search_path TO {schema}, public"))
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
