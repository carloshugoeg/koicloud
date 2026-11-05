"""Unique per-call probe ponds for GET /ponds/{id}/schema tests (parallel-safe)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.crypto import encrypt_secret
from app.core.security import hash_password, hash_token
from tests.db_reset import DEMO_EMAIL, ensure_demo_user

# Same password as tests/sql_probe_pond.py so probes do not fight over the role.
PROBE_PASSWORD = "pond-sql-test"
PROBE_HOST = "127.0.0.1"
PROBE_PORT = 5432


@dataclass(frozen=True, slots=True)
class SchemaProbePond:
    pond_id: UUID
    user_id: UUID
    database: str
    node_id: str
    name: str


def _admin_url(database: str) -> str:
    base = to_sync_database_url(get_settings().database_url).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return base.rsplit("/", 1)[0] + f"/{database}"


def _ensure_postgres_role() -> None:
    with psycopg.connect(_admin_url("postgres"), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'postgres'").fetchone()
        if exists is None:
            conn.execute(
                sql.SQL("CREATE ROLE postgres LOGIN SUPERUSER PASSWORD {}").format(
                    sql.Literal(PROBE_PASSWORD)
                )
            )
        else:
            # Keep password in sync with sql_probe_pond without surprising other suites.
            conn.execute(
                sql.SQL("ALTER ROLE postgres WITH LOGIN SUPERUSER PASSWORD {}").format(
                    sql.Literal(PROBE_PASSWORD)
                )
            )


def _prepare_database(database: str, *, with_tables: bool) -> None:
    _ensure_postgres_role()
    with psycopg.connect(_admin_url("postgres"), autocommit=True) as conn:
        conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (database,),
        )
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))
        conn.execute(
            sql.SQL("CREATE DATABASE {} OWNER postgres").format(sql.Identifier(database))
        )
    if not with_tables:
        return
    with psycopg.connect(_admin_url(database), autocommit=True) as conn:
        conn.execute(
            """
            CREATE TABLE public.orders (
                id integer PRIMARY KEY,
                label text NOT NULL DEFAULT 'x',
                qty integer
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE public.items (
                sku text PRIMARY KEY,
                price numeric(10, 2) NOT NULL
            )
            """
        )
        conn.execute("INSERT INTO public.orders (id, label, qty) VALUES (1, 'a', 3)")
        conn.execute("INSERT INTO public.orders (id, label, qty) VALUES (2, 'b', NULL)")
        conn.execute("INSERT INTO public.items (sku, price) VALUES ('s1', 1.50)")
        conn.execute("ANALYZE public.orders")
        conn.execute("ANALYZE public.items")


def _clear_schema_probe_rows(connection) -> None:
    """Drop prior schema-probe ponds so host_port 5432 stays unique (one live probe)."""
    connection.execute(
        text(
            """
            DELETE FROM pond_status
            WHERE pond_id IN (
                SELECT id FROM ponds
                WHERE name LIKE 'schema-p-%' OR name LIKE 'schema-f-%' OR host_port = :port
            )
            """
        ),
        {"port": PROBE_PORT},
    )
    connection.execute(
        text(
            """
            DELETE FROM ponds
            WHERE name LIKE 'schema-p-%' OR name LIKE 'schema-f-%' OR host_port = :port
            """
        ),
        {"port": PROBE_PORT},
    )
    connection.execute(
        text("DELETE FROM nodes WHERE id LIKE 'node-schema-%'")
    )


def seed_schema_pond(*, with_tables: bool = False) -> SchemaProbePond:
    """Insert one owned running pond backed by a uniquely named database."""
    ensure_demo_user()
    suffix = uuid4().hex[:10]
    pond_name = f"schema-p-{suffix}"
    database = pond_name.replace("-", "_")
    node_id = f"node-schema-{suffix}"
    pond_id = uuid4()
    _prepare_database(database, with_tables=with_tables)

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        _clear_schema_probe_rows(connection)
        user_id = connection.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": DEMO_EMAIL},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO nodes (id, public_host, status, capacity_ponds, token_hash)
                VALUES (:id, :host, 'alive', 20, :token_hash)
                """
            ),
            {
                "id": node_id,
                "host": PROBE_HOST,
                "token_hash": hash_token(f"schema-{suffix}"),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO ponds (
                    id, user_id, plan_id, node_id, name, engine_version,
                    desired_state, host_port, db_password_encrypted
                )
                VALUES (
                    :id, :user_id, 'micro', :node_id, :name, '16',
                    'running', :port, :password
                )
                """
            ),
            {
                "id": pond_id,
                "user_id": user_id,
                "node_id": node_id,
                "name": pond_name,
                "port": PROBE_PORT,
                "password": encrypt_secret(PROBE_PASSWORD),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO pond_status (pond_id, observed_state, healthy, updated_at)
                VALUES (:id, 'running', true, CURRENT_TIMESTAMP)
                """
            ),
            {"id": pond_id},
        )
    engine.dispose()
    return SchemaProbePond(
        pond_id=pond_id,
        user_id=user_id,
        database=database,
        node_id=node_id,
        name=pond_name,
    )


def mark_pond_stopped(pond_id: UUID) -> None:
    # Unique dead port: observed_state gate fires before connect, so the port
    # only needs to stay unique under ponds_host_port_uk.
    dead_port = 16000 + (pond_id.int % 4000)
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE ponds
                SET desired_state = 'stopped', host_port = :port
                WHERE id = :id
                """
            ),
            {"id": pond_id, "port": dead_port},
        )
        connection.execute(
            text(
                """
                UPDATE pond_status
                SET observed_state = 'stopped', healthy = false
                WHERE pond_id = :id
                """
            ),
            {"id": pond_id},
        )
    engine.dispose()


def create_foreign_owner_pond() -> tuple[SchemaProbePond, str, str]:
    """Pond owned by a second user. Returns (pond, foreign_email, foreign_password)."""
    ensure_demo_user()
    suffix = uuid4().hex[:10]
    foreign_email = f"foreign-{suffix}@koicloud.dev"
    foreign_password = "Sup3rSegura!2026"
    pond_name = f"schema-f-{suffix}"
    database = pond_name.replace("-", "_")
    node_id = f"node-schema-f-{suffix}"
    pond_id = uuid4()
    _prepare_database(database, with_tables=False)

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        _clear_schema_probe_rows(connection)
        foreign_user_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO users (
                    id, email, password_hash, full_name, role, status, email_verified_at
                )
                VALUES (
                    :id, :email, :password_hash, :full_name, 'client', 'active', CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": foreign_user_id,
                "email": foreign_email,
                "password_hash": hash_password(foreign_password),
                "full_name": "Foreign Owner",
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO nodes (id, public_host, status, capacity_ponds, token_hash)
                VALUES (:id, :host, 'alive', 20, :token_hash)
                """
            ),
            {
                "id": node_id,
                "host": PROBE_HOST,
                "token_hash": hash_token(f"schema-f-{suffix}"),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO ponds (
                    id, user_id, plan_id, node_id, name, engine_version,
                    desired_state, host_port, db_password_encrypted
                )
                VALUES (
                    :id, :user_id, 'micro', :node_id, :name, '16',
                    'running', :port, :password
                )
                """
            ),
            {
                "id": pond_id,
                "user_id": foreign_user_id,
                "node_id": node_id,
                "name": pond_name,
                "port": PROBE_PORT,
                "password": encrypt_secret(PROBE_PASSWORD),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO pond_status (pond_id, observed_state, healthy, updated_at)
                VALUES (:id, 'running', true, CURRENT_TIMESTAMP)
                """
            ),
            {"id": pond_id},
        )
    engine.dispose()
    pond = SchemaProbePond(
        pond_id=pond_id,
        user_id=foreign_user_id,
        database=database,
        node_id=node_id,
        name=pond_name,
    )
    return pond, foreign_email, foreign_password
