from __future__ import annotations

import base64
import hashlib

import asyncpg

CONSOLE_ROLE = "koi_console"
APP_SCHEMA = "app"
_PASSWORD_GUC = "koicloud.console_password"
_FORBIDDEN_ROLES = (
    "pg_read_server_files",
    "pg_write_server_files",
    "pg_execute_server_program",
)


def console_role_password(pond_password: str) -> str:
    digest = hashlib.sha256(
        b"koicloud.console-role.v1\0" + pond_password.encode("utf-8")
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


async def ensure_console_role(conn: asyncpg.Connection, password: str) -> None:
    """Make koi_console match the console contract. Safe to run again."""
    await conn.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{CONSOLE_ROLE}') THEN
            CREATE ROLE {CONSOLE_ROLE} LOGIN;
          END IF;
        END $$
        """
    )
    await conn.execute(
        "SELECT set_config($1, $2, false)",
        _PASSWORD_GUC,
        password,
    )
    await conn.execute(
        f"""
        DO $$
        BEGIN
          EXECUTE format(
            'ALTER ROLE {CONSOLE_ROLE} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE '
            'NOREPLICATION NOBYPASSRLS PASSWORD %L',
            current_setting('{_PASSWORD_GUC}')
          );
        END $$
        """
    )
    await conn.execute("SELECT set_config($1, '', false)", _PASSWORD_GUC)
    revoked = ", ".join(_FORBIDDEN_ROLES)
    await conn.execute(f"REVOKE {revoked} FROM {CONSOLE_ROLE}")
    await conn.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = '{APP_SCHEMA}') THEN
            CREATE SCHEMA {APP_SCHEMA} AUTHORIZATION {CONSOLE_ROLE};
          END IF;
        END $$
        """
    )
    await conn.execute(f"ALTER SCHEMA {APP_SCHEMA} OWNER TO {CONSOLE_ROLE}")
    await conn.execute(f"GRANT USAGE, CREATE ON SCHEMA {APP_SCHEMA} TO {CONSOLE_ROLE}")
    await conn.execute(f"GRANT USAGE ON SCHEMA public TO {CONSOLE_ROLE}")
    await conn.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {CONSOLE_ROLE}"
    )
    await conn.execute(
        f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {CONSOLE_ROLE}"
    )
    await conn.execute(
        f"""
        DO $$
        DECLARE
          rel record;
        BEGIN
          FOR rel IN
            SELECT c.oid::regclass AS obj, c.relkind
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = '{APP_SCHEMA}'
              AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
              AND c.relowner <> (SELECT oid FROM pg_roles WHERE rolname = '{CONSOLE_ROLE}')
          LOOP
            IF rel.relkind = 'S' THEN
              EXECUTE format('ALTER SEQUENCE %s OWNER TO {CONSOLE_ROLE}', rel.obj);
            ELSIF rel.relkind = 'v' THEN
              EXECUTE format('ALTER VIEW %s OWNER TO {CONSOLE_ROLE}', rel.obj);
            ELSIF rel.relkind = 'm' THEN
              EXECUTE format('ALTER MATERIALIZED VIEW %s OWNER TO {CONSOLE_ROLE}', rel.obj);
            ELSIF rel.relkind = 'f' THEN
              EXECUTE format('ALTER FOREIGN TABLE %s OWNER TO {CONSOLE_ROLE}', rel.obj);
            ELSE
              EXECUTE format('ALTER TABLE %s OWNER TO {CONSOLE_ROLE}', rel.obj);
            END IF;
          END LOOP;
        END $$
        """
    )
    await conn.execute(
        f"""
        DO $$
        BEGIN
          EXECUTE format(
            'GRANT CONNECT, TEMP ON DATABASE %I TO {CONSOLE_ROLE}',
            current_database()
          );
          EXECUTE format(
            'ALTER ROLE {CONSOLE_ROLE} IN DATABASE %I SET search_path TO {APP_SCHEMA}, public',
            current_database()
          );
        END $$
        """
    )
