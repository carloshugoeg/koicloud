"""A real Postgres database reached through a pond row.

The console must use the pond's host, port, and password. This module
creates that database and the pond row the command looks up. It is not a
stand-in result.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.crypto import encrypt_secret
from app.core.security import hash_token
from tests.db_reset import DEMO_EMAIL, ensure_demo_user, reset_pond_tables

POND_NAME = "sql-probe"
PROBE_DATABASE = "sql_probe"
PROBE_PASSWORD = "pond-sql-test"
PROBE_HOST = "127.0.0.1"
PROBE_PORT = 5432
PROBE_QUERY = "SELECT n FROM probe"
PROBE_VALUE = 42


@dataclass(frozen=True, slots=True)
class ProbePond:
    pond_id: UUID
    user_id: UUID


def _admin_url(database: str) -> str:
    base = to_sync_database_url(get_settings().database_url).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return base.rsplit("/", 1)[0] + f"/{database}"


def _prepare_probe_database() -> None:
    with psycopg.connect(_admin_url("postgres"), autocommit=True) as conn:
        conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (PROBE_DATABASE,),
        )
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(PROBE_DATABASE))
        )
        conn.execute(
            sql.SQL("CREATE DATABASE {} OWNER postgres").format(sql.Identifier(PROBE_DATABASE))
        )
    with psycopg.connect(_admin_url(PROBE_DATABASE), autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS probe")
        conn.execute("CREATE TABLE probe (n integer NOT NULL)")
        conn.execute("INSERT INTO probe (n) VALUES (%s)", (PROBE_VALUE,))


def probe_values() -> list[int]:
    with psycopg.connect(
        f"postgresql://postgres:{PROBE_PASSWORD}@{PROBE_HOST}:{PROBE_PORT}/{PROBE_DATABASE}",
        autocommit=True,
    ) as conn:
        rows = conn.execute("SELECT n FROM probe ORDER BY n").fetchall()
    return [int(row[0]) for row in rows]


def seed_probe_pond() -> ProbePond:
    _prepare_probe_database()
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM sql_history"))
    engine.dispose()
    reset_pond_tables()
    ensure_demo_user()

    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        user_id = connection.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": DEMO_EMAIL},
        ).scalar_one()
        pond_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO nodes (id, public_host, status, capacity_ponds, token_hash)
                VALUES (:id, :host, 'alive', 20, :token_hash)
                """
            ),
            {
                "id": "node-sql-probe",
                "host": PROBE_HOST,
                "token_hash": hash_token("sql-probe-node"),
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
                    :id, :user_id, 'micro', 'node-sql-probe', :name, '16',
                    'running', :port, :password
                )
                """
            ),
            {
                "id": pond_id,
                "user_id": user_id,
                "name": POND_NAME,
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
    return ProbePond(pond_id=pond_id, user_id=user_id)


if __name__ == "__main__":
    print(seed_probe_pond().pond_id)
