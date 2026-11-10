"""Restore must succeed on dumps with SERIAL and IDENTITY columns (PG 16).

Sequences linked to a table column cannot take ALTER SEQUENCE ... OWNER TO
(SQLSTATE 0A000); they follow the table owner instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from psycopg import sql as pg_sql

from app.core.config import get_settings, to_sync_database_url

_AGENT_ROOT = Path(__file__).resolve().parents[3] / "apps" / "node-agent"
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

DATABASE = "restore_serial_identity_probe"

DUMP = b"""SET statement_timeout = 0;
CREATE TABLE public.items (
    id serial PRIMARY KEY,
    code integer GENERATED ALWAYS AS IDENTITY,
    name text NOT NULL
);
INSERT INTO public.items (name) VALUES ('alpha'), ('beta');
CREATE SEQUENCE public.free_counter;
"""


def _url(database: str) -> str:
    base = to_sync_database_url(get_settings().database_url).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return base.rsplit("/", 1)[0] + f"/{database}"


def _fresh_database() -> None:
    with psycopg.connect(_url("postgres"), autocommit=True) as conn:
        conn.execute(
            pg_sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(pg_sql.Identifier(DATABASE))
        )
        conn.execute(pg_sql.SQL("CREATE DATABASE {}").format(pg_sql.Identifier(DATABASE)))


def _apply(script: bytes) -> None:
    with psycopg.connect(_url(DATABASE), autocommit=True) as conn:
        conn.execute(script.decode("utf-8"))


def test_restore_of_serial_and_identity_dump_succeeds_and_reowns_objects() -> None:
    from agent.drivers.docker_driver import restore_script

    _fresh_database()
    # Twice: the second run replaces a schema that already holds linked sequences.
    for _ in range(2):
        try:
            _apply(restore_script(DUMP))
        except psycopg.Error as error:
            raise AssertionError(f"restore failed sqlstate={error.sqlstate}: {error}") from error

    with psycopg.connect(_url(DATABASE)) as conn:
        names = [row[0] for row in conn.execute("SELECT name FROM public.items ORDER BY id")]
        owners = dict(
            conn.execute(
                """
                SELECT c.relname, pg_get_userbyid(c.relowner)
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'S')
                """
            ).fetchall()
        )
    assert names == ["alpha", "beta"]
    assert owners["items"] == "koi_console"
    assert owners["items_id_seq"] == "koi_console"
    assert owners["items_code_seq"] == "koi_console"
    assert owners["free_counter"] == "koi_console"
