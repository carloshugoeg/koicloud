from __future__ import annotations

import base64
import hashlib

_SQL = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'koi_console') THEN
    CREATE ROLE koi_console LOGIN;
  END IF;
END $$;
ALTER ROLE koi_console WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'console_password';
REVOKE pg_read_server_files, pg_write_server_files, pg_execute_server_program FROM koi_console;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'app') THEN
    CREATE SCHEMA app AUTHORIZATION koi_console;
  END IF;
END $$;
ALTER SCHEMA app OWNER TO koi_console;
GRANT USAGE, CREATE ON SCHEMA app TO koi_console;
GRANT USAGE ON SCHEMA public TO koi_console;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO koi_console;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO koi_console;
DO $$
DECLARE
  rel record;
BEGIN
  FOR rel IN
    SELECT c.oid::regclass AS obj, c.relkind
    FROM pg_class AS c
    JOIN pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = 'app'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
      AND c.relowner <> (SELECT oid FROM pg_roles WHERE rolname = 'koi_console')
  LOOP
    IF rel.relkind = 'S' THEN
      EXECUTE format('ALTER SEQUENCE %s OWNER TO koi_console', rel.obj);
    ELSIF rel.relkind = 'v' THEN
      EXECUTE format('ALTER VIEW %s OWNER TO koi_console', rel.obj);
    ELSIF rel.relkind = 'm' THEN
      EXECUTE format('ALTER MATERIALIZED VIEW %s OWNER TO koi_console', rel.obj);
    ELSIF rel.relkind = 'f' THEN
      EXECUTE format('ALTER FOREIGN TABLE %s OWNER TO koi_console', rel.obj);
    ELSE
      EXECUTE format('ALTER TABLE %s OWNER TO koi_console', rel.obj);
    END IF;
  END LOOP;
END $$;
GRANT CONNECT, TEMP ON DATABASE :"db" TO koi_console;
ALTER ROLE koi_console IN DATABASE :"db" SET search_path TO app, public;
"""


def console_role_password(pond_password: str) -> str:
    digest = hashlib.sha256(
        b"koicloud.console-role.v1\0" + pond_password.encode("utf-8")
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def console_role_environment(database: str, pond_password: str) -> dict[str, str]:
    return {
        "PGPASSWORD": pond_password,
        "KOI_DB": database,
        "KOI_CONSOLE_PASSWORD": console_role_password(pond_password),
        "KOI_SQL": _SQL,
    }


def console_role_argv() -> list[str]:
    return [
        "sh",
        "-c",
        (
            "printf '%s\\n' \"$KOI_SQL\" | psql -U postgres -d \"$KOI_DB\" "
            "-v ON_ERROR_STOP=1 -v console_password=\"$KOI_CONSOLE_PASSWORD\" "
            "-v db=\"$KOI_DB\" -f -"
        ),
    ]
