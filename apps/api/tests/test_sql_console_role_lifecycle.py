"""Console role lifecycle against PostgreSQL 16.

Ten parallel queries must all succeed, the console password must stay out of
the server log and out of captured errors, an existing pond must still accept
CREATE, ALTER, and TRUNCATE, the role must not connect to another database,
and a second query must not rewrite the role when the password is unchanged.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from urllib.parse import quote

import asyncpg
import httpx
import psycopg
import pytest
from httpx import ASGITransport
from psycopg import sql as pg_sql

from app.commands import sql as sql_command
from app.commands.sql import run_sql
from app.core.auth import AuthContext
from app.core.config import get_settings, to_sync_database_url
from app.core.crypto import encrypt_secret
from app.core.enums import AppSurface, SQLMode, UserRole, UserStatus
from app.main import app
from app.modules.ponds.console_role import (
    _SETUP_SQL,
    console_role_password,
    ensure_console_role,
    scram_sha256_verifier,
)
from app.schemas import RunSQLRequest
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD
from tests.sql_probe_pond import PROBE_DATABASE, PROBE_PASSWORD, seed_probe_pond

OTHER_DATABASE = "sql_probe_other"
SERIAL_PROBE_DATABASE = "sql_serial_probe"
CONSOLE_ROLE = "koi_console"


def _admin(database: str) -> str:
    base = to_sync_database_url(get_settings().database_url).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return base.rsplit("/", 1)[0] + f"/{database}"


def _actor(user_id: object) -> AuthContext:
    return AuthContext(
        user_id=str(user_id),
        email=DEMO_EMAIL,
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        surface=AppSurface.WEB,
    )


def _secret() -> str:
    return console_role_password(PROBE_PASSWORD)


def _drop_console_role() -> None:
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (CONSOLE_ROLE,),
        ).fetchone()
        databases = [
            row[0]
            for row in conn.execute(
                """
                SELECT datname FROM pg_database
                WHERE datallowconn AND NOT datistemplate
                """
            ).fetchall()
        ]
    if exists is None:
        return
    for name in databases:
        with psycopg.connect(_admin(name), autocommit=True) as conn:
            conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE usename = %s AND pid <> pg_backend_pid()
                """,
                (CONSOLE_ROLE,),
            )
            conn.execute(f"DROP OWNED BY {CONSOLE_ROLE}")
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        conn.execute(f"DROP ROLE IF EXISTS {CONSOLE_ROLE}")


def _ensure_other_database() -> None:
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (OTHER_DATABASE,),
        )
        conn.execute(f"DROP DATABASE IF EXISTS {OTHER_DATABASE}")
        conn.execute(f"CREATE DATABASE {OTHER_DATABASE}")


def _log_offset() -> int | None:
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        row = conn.execute("SELECT pg_current_logfile()").fetchone()
        if row is None or not row[0]:
            return None
        size = conn.execute("SELECT size FROM pg_stat_file(%s)", (row[0],)).fetchone()
    return int(size[0]) if size else 0


def _log_since(offset: int | None) -> str:
    if offset is None:
        return ""
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        name = conn.execute("SELECT pg_current_logfile()").fetchone()
        if name is None or not name[0]:
            return ""
        size = conn.execute("SELECT size FROM pg_stat_file(%s)", (name[0],)).fetchone()
        length = max(0, int(size[0]) - offset)
        if length == 0:
            return ""
        chunk = conn.execute(
            "SELECT pg_read_file(%s, %s, %s)",
            (name[0], offset, length),
        ).fetchone()
    return chunk[0] if chunk and chunk[0] else ""


def _captured(error: BaseException) -> str:
    parts = [str(error)]
    for attr in ("message", "detail", "hint", "context", "query"):
        value = getattr(error, attr, None)
        if value:
            parts.append(str(value))
    if error.__cause__ is not None:
        parts.append(_captured(error.__cause__))
    return "\n".join(parts)


def _secret_hits(blob: str) -> list[str]:
    problems: list[str] = []
    secret = _secret()
    if secret in blob:
        problems.append(f"console password ({blob.count(secret)} hits)")
    if PROBE_PASSWORD in blob:
        problems.append(f"pond password ({blob.count(PROBE_PASSWORD)} hits)")
    return problems


def _role_xmin() -> str:
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        row = conn.execute(
            "SELECT xmin::text FROM pg_authid WHERE rolname = %s",
            (CONSOLE_ROLE,),
        ).fetchone()
    assert row is not None
    return str(row[0])


async def _login(http: httpx.AsyncClient) -> dict[str, str]:
    response = await http.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _ten_http(pond_id: object) -> list[httpx.Response]:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        headers = await _login(http)
        responses = await asyncio.gather(
            *[
                http.post(
                    f"/api/v1/ponds/{pond_id}/sql",
                    headers=headers,
                    json={"query": "SELECT 1 AS n", "mode": "read"},
                )
                for _ in range(10)
            ]
        )
    return list(responses)


async def test_ten_parallel_console_queries_all_succeed() -> None:
    pond = seed_probe_pond()
    _drop_console_role()
    responses = await _ten_http(pond.pond_id)
    statuses = [response.status_code for response in responses]
    leaked = [
        response.status_code
        for response in responses
        if "tuple concurrently updated" in response.text
    ]
    assert statuses == [200] * 10, statuses
    assert leaked == []


async def test_console_password_never_reaches_the_log_or_captured_errors() -> None:
    pond = seed_probe_pond()
    _drop_console_role()
    offset = _log_offset()
    actor = _actor(pond.user_id)
    results = await asyncio.gather(
        *[
            run_sql(
                pond.pond_id,
                RunSQLRequest(query="SELECT 1 AS n", mode=SQLMode.READ),
                actor=actor,
                surface=AppSurface.WEB,
            )
            for _ in range(10)
        ],
        return_exceptions=True,
    )
    captured = "\n".join(_captured(item) for item in results if isinstance(item, BaseException))
    log = _log_since(offset)
    problems = [f"captured errors contain the {hit}" for hit in _secret_hits(captured)]
    problems.extend(f"postgres log contains the {hit}" for hit in _secret_hits(log))
    assert problems == [], "; ".join(problems)


def test_console_can_create_alter_and_truncate_postgres_owned_objects() -> None:
    pond = seed_probe_pond()
    with psycopg.connect(_admin(PROBE_DATABASE), autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS app CASCADE")
        conn.execute("CREATE SCHEMA app AUTHORIZATION postgres")
        conn.execute("CREATE TABLE app.legacy (n integer)")
        conn.execute("INSERT INTO app.legacy (n) VALUES (3)")
        conn.execute("ALTER TABLE app.legacy OWNER TO postgres")
        conn.execute("ALTER TABLE probe OWNER TO postgres")

    transport = ASGITransport(app=app)

    async def _write(query: str) -> httpx.Response:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            headers = await _login(http)
            return await http.post(
                f"/api/v1/ponds/{pond.pond_id}/sql",
                headers=headers,
                json={"query": query, "mode": "write"},
            )

    altered = asyncio.run(_write("ALTER TABLE probe ADD COLUMN extra text"))
    truncated = asyncio.run(_write("TRUNCATE probe"))
    legacy = asyncio.run(_write("ALTER TABLE app.legacy ADD COLUMN note text"))
    created = asyncio.run(_write("CREATE TABLE public.fresh (n integer)"))
    inserted = asyncio.run(_write("INSERT INTO public.fresh (n) VALUES (4)"))
    selected = asyncio.run(_write("SELECT n FROM public.fresh"))

    assert altered.status_code == 200, altered.text
    assert truncated.status_code == 200, truncated.text
    assert legacy.status_code == 200, legacy.text
    assert created.status_code == 200, created.text
    assert inserted.status_code == 200, inserted.text
    assert selected.status_code == 200, selected.text
    assert selected.json()["rows"] == [[4]]


def _prepare_fresh_serial_identity_database(database: str) -> None:
    """Create a brand-new DB whose only user tables use SERIAL and IDENTITY.

    A reused catalog can change peer scan order and hide the PG 16 0A000 on
    linked sequences, so this always DROP/CREATE the database first.
    """
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (database,),
        )
        conn.execute(pg_sql.SQL("DROP DATABASE IF EXISTS {}").format(pg_sql.Identifier(database)))
        conn.execute(
            pg_sql.SQL("CREATE DATABASE {} OWNER postgres").format(pg_sql.Identifier(database))
        )
    with psycopg.connect(_admin(database), autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE public.serial_legacy (id SERIAL PRIMARY KEY, label text NOT NULL)"
        )
        conn.execute(
            """
            CREATE TABLE public.identity_legacy (
              id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
              label text NOT NULL
            )
            """
        )
        conn.execute("INSERT INTO public.serial_legacy (label) VALUES ('s1')")
        conn.execute("INSERT INTO public.identity_legacy (label) VALUES ('i1')")


def _seed_postgres_owned_serial_and_identity_tables() -> None:
    """Leave SERIAL and IDENTITY columns on the probe pond, owned by postgres."""
    with psycopg.connect(_admin(PROBE_DATABASE), autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS public.serial_legacy CASCADE")
        conn.execute("DROP TABLE IF EXISTS public.identity_legacy CASCADE")
        conn.execute(
            "CREATE TABLE public.serial_legacy (id SERIAL PRIMARY KEY, label text NOT NULL)"
        )
        conn.execute(
            """
            CREATE TABLE public.identity_legacy (
              id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
              label text NOT NULL
            )
            """
        )
        conn.execute("INSERT INTO public.serial_legacy (label) VALUES ('s1')")
        conn.execute("INSERT INTO public.identity_legacy (label) VALUES ('i1')")
        conn.execute("ALTER TABLE public.serial_legacy OWNER TO postgres")
        conn.execute("ALTER TABLE public.identity_legacy OWNER TO postgres")
        conn.execute("ALTER TABLE public.probe OWNER TO postgres")


def _run_setup_sql_via_peer_psql(database: str) -> subprocess.CompletedProcess[str]:
    """Run the API setup body over a local peer session.

    Peer plans on a fresh serial-only catalog visit linked sequences before
    their tables, which is the PG 16 failure mode for ALTER SEQUENCE OWNER TO.
    """
    verifier = scram_sha256_verifier(_secret(), os.urandom(16))
    script = (
        "BEGIN;\n"
        "SELECT pg_advisory_xact_lock(hashtext('koicloud.console-role.v1'));\n"
        f"SELECT set_config('koicloud.console_verifier', '{verifier}', true);\n"
        f"{_SETUP_SQL}\n"
        "COMMIT;\n"
    )
    return subprocess.run(
        [
            "sudo",
            "-n",
            "-u",
            "postgres",
            "psql",
            "-d",
            database,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            "-",
        ],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )


def test_console_setup_succeeds_on_serial_and_identity_pond() -> None:
    _drop_console_role()
    _prepare_fresh_serial_identity_database(SERIAL_PROBE_DATABASE)
    result = _run_setup_sql_via_peer_psql(SERIAL_PROBE_DATABASE)
    assert result.returncode == 0, result.stderr or result.stdout


async def test_console_query_succeeds_on_pond_with_serial_and_identity() -> None:
    pond = seed_probe_pond()
    _drop_console_role()
    _seed_postgres_owned_serial_and_identity_tables()
    response = await _one_read(pond.pond_id)
    assert response.status_code == 200, response.text
    assert response.json().get("code") != "internal_error"


async def test_console_can_insert_into_serial_and_identity_on_existing_pond() -> None:
    pond = seed_probe_pond()
    _drop_console_role()
    _seed_postgres_owned_serial_and_identity_tables()
    transport = ASGITransport(app=app)

    async def _write(query: str) -> httpx.Response:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            headers = await _login(http)
            return await http.post(
                f"/api/v1/ponds/{pond.pond_id}/sql",
                headers=headers,
                json={"query": query, "mode": "write"},
            )

    serial_insert = await _write(
        "INSERT INTO public.serial_legacy (label) VALUES ('s2') RETURNING id"
    )
    identity_insert = await _write(
        "INSERT INTO public.identity_legacy (label) VALUES ('i2') RETURNING id"
    )
    assert serial_insert.status_code == 200, serial_insert.text
    assert identity_insert.status_code == 200, identity_insert.text
    assert serial_insert.json()["rows"] == [[2]]
    assert identity_insert.json()["rows"] == [[2]]


def test_console_role_cannot_connect_to_another_database() -> None:
    pond = seed_probe_pond()
    _ensure_other_database()
    transport = ASGITransport(app=app)

    async def _read() -> httpx.Response:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            headers = await _login(http)
            return await http.post(
                f"/api/v1/ponds/{pond.pond_id}/sql",
                headers=headers,
                json={"query": "SELECT 1", "mode": "read"},
            )

    ready = asyncio.run(_read())
    assert ready.status_code == 200, ready.text
    password = quote(_secret(), safe="")
    own = f"postgresql://{CONSOLE_ROLE}:{password}@127.0.0.1:5432/{PROBE_DATABASE}"
    other = f"postgresql://{CONSOLE_ROLE}:{password}@127.0.0.1:5432/{OTHER_DATABASE}"
    with psycopg.connect(own, connect_timeout=5) as conn:
        who = conn.execute("SELECT current_user").fetchone()
    assert who is not None
    assert who[0] == CONSOLE_ROLE
    with pytest.raises(psycopg.OperationalError) as raised:
        psycopg.connect(other, connect_timeout=5)
    assert "authentication failed" not in str(raised.value).lower()


def test_console_setup_does_not_rerun_when_the_password_is_unchanged() -> None:
    pond = seed_probe_pond()
    transport = ASGITransport(app=app)

    async def _read() -> httpx.Response:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            headers = await _login(http)
            return await http.post(
                f"/api/v1/ponds/{pond.pond_id}/sql",
                headers=headers,
                json={"query": "SELECT 1", "mode": "read"},
            )

    first = asyncio.run(_read())
    assert first.status_code == 200, first.text
    before = _role_xmin()
    second = asyncio.run(_read())
    assert second.status_code == 200, second.text
    assert _role_xmin() == before


LATER_QUERIES = 4
ROTATED_POND_PASSWORD = "pond-sql-rotated"


def _stored_salt() -> str:
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        row = conn.execute(
            "SELECT rolpassword FROM pg_authid WHERE rolname = %s",
            (CONSOLE_ROLE,),
        ).fetchone()
    if row is None or not row[0]:
        raise AssertionError("console role has no stored password")
    parts = str(row[0]).split("$")
    if len(parts) < 3 or ":" not in parts[1]:
        raise AssertionError("stored role password is not a SCRAM verifier")
    return parts[1].split(":", 1)[1]


def _set_postgres_password(password: str) -> None:
    statement = pg_sql.SQL("ALTER USER postgres PASSWORD {}").format(pg_sql.Literal(password))
    with psycopg.connect(_admin("postgres"), autocommit=True) as conn:
        conn.execute(statement)


def _restore_public_schema() -> None:
    with psycopg.connect(_admin(PROBE_DATABASE), autocommit=True) as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS public AUTHORIZATION postgres")


def _set_pond_secret(pond_id: object, password: str) -> None:
    url = to_sync_database_url(get_settings().database_url).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "UPDATE ponds SET db_password_encrypted = %s WHERE id = %s",
            (encrypt_secret(password), pond_id),
        )


def _count_setup(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []
    real = sql_command.ensure_console_role

    async def counting(conn: asyncpg.Connection, password: str) -> None:
        calls.append(1)
        await real(conn, password)

    monkeypatch.setattr(sql_command, "ensure_console_role", counting)
    return calls


async def _one_read(pond_id: object) -> httpx.Response:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        headers = await _login(http)
        return await http.post(
            f"/api/v1/ponds/{pond_id}/sql",
            headers=headers,
            json={"query": "SELECT 1 AS n", "mode": "read"},
        )


async def test_later_console_queries_do_not_run_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pond = seed_probe_pond()
    _drop_console_role()
    calls = _count_setup(monkeypatch)
    first = await _one_read(pond.pond_id)
    assert first.status_code == 200
    before = _role_xmin()
    del calls[:]
    for _ in range(LATER_QUERIES):
        response = await _one_read(pond.pond_id)
        assert response.status_code == 200
    if calls:
        raise AssertionError(f"later console queries ran setup {len(calls)} times")
    if _role_xmin() != before:
        raise AssertionError("later console queries rewrote the console role")


async def test_two_ponds_store_different_scram_salts() -> None:
    seed_probe_pond()
    _drop_console_role()
    console_password = console_role_password("shared-pond-password")
    connection = await asyncpg.connect(_admin(PROBE_DATABASE))
    try:
        await ensure_console_role(connection, console_password)
        salt_a = _stored_salt()
        _drop_console_role()
        _restore_public_schema()
        await ensure_console_role(connection, console_password)
        salt_b = _stored_salt()
        if salt_a == salt_b:
            raise AssertionError("two ponds stored the same SCRAM salt")
        await ensure_console_role(connection, console_password)
        if _stored_salt() != salt_b:
            raise AssertionError("a second setup for the same password changed the SCRAM salt")
    finally:
        await connection.close()


async def test_password_rotation_runs_setup_once(monkeypatch: pytest.MonkeyPatch) -> None:
    pond = seed_probe_pond()
    _drop_console_role()
    first = await _one_read(pond.pond_id)
    assert first.status_code == 200
    salt_before = _stored_salt()
    calls = _count_setup(monkeypatch)
    try:
        _set_postgres_password(ROTATED_POND_PASSWORD)
        _set_pond_secret(pond.pond_id, ROTATED_POND_PASSWORD)
        rotated = await _one_read(pond.pond_id)
        assert rotated.status_code == 200
        for _ in range(LATER_QUERIES):
            follow = await _one_read(pond.pond_id)
            assert follow.status_code == 200
        if len(calls) != 1:
            raise AssertionError(f"password rotation ran setup {len(calls)} times")
        if _stored_salt() == salt_before:
            raise AssertionError("password rotation kept the previous SCRAM salt")
    finally:
        _set_postgres_password(PROBE_PASSWORD)
