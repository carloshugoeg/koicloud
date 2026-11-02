from __future__ import annotations

import base64
import hashlib
import hmac
import os

import asyncpg

CONSOLE_ROLE = "koi_console"
_SCRAM_ITERATIONS = 4096
_SALT_BYTES = 16

# Same body as apps/node-agent/agent/console_role.py. The verifier arrives
# through koicloud.console_verifier, never as a plaintext password.
_SETUP_SQL = """
DO $console$
DECLARE
  expected text := current_setting('koicloud.console_verifier');
  current text;
  sch text;
  rel record;
  dbname text;
BEGIN
  SELECT rolpassword INTO current
  FROM pg_authid
  WHERE rolname = 'koi_console';
  -- The role password is cluster-wide. Ownership and CONNECT are per database,
  -- so a matching verifier is not enough when this pond still needs repair.
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'koi_console')
     AND current IS NOT DISTINCT FROM expected
     AND NOT EXISTS (
       SELECT 1
       FROM pg_namespace AS n
       JOIN pg_roles AS r ON r.oid = n.nspowner
       WHERE n.nspname <> 'information_schema'
         AND n.nspname NOT LIKE 'pg_%'
         AND r.rolname <> 'koi_console'
     )
     AND NOT EXISTS (
       SELECT 1
       FROM pg_class AS c
       JOIN pg_namespace AS n ON n.oid = c.relnamespace
       JOIN pg_roles AS r ON r.oid = c.relowner
       WHERE n.nspname <> 'information_schema'
         AND n.nspname NOT LIKE 'pg_%'
         AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f', 'i')
         AND r.rolname <> 'koi_console'
     )
     AND NOT EXISTS (
       SELECT 1
       FROM pg_database AS d
       WHERE d.datallowconn
         AND d.datname <> current_database()
         AND (
           has_database_privilege('public', d.datname, 'CONNECT')
           OR has_database_privilege('koi_console', d.datname, 'CONNECT')
         )
     )
  THEN
    RETURN;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'koi_console') THEN
    CREATE ROLE koi_console LOGIN;
  END IF;
  ALTER ROLE koi_console WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
  REVOKE pg_read_server_files, pg_write_server_files, pg_execute_server_program
    FROM koi_console;

  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'app') THEN
    CREATE SCHEMA app AUTHORIZATION koi_console;
  END IF;

  FOR sch IN
    SELECT n.nspname
    FROM pg_namespace AS n
    WHERE n.nspname <> 'information_schema'
      AND n.nspname NOT LIKE 'pg_%'
  LOOP
    EXECUTE format('ALTER SCHEMA %I OWNER TO koi_console', sch);
  END LOOP;

  FOR rel IN
    SELECT c.oid::regclass::text AS obj, c.relkind
    FROM pg_class AS c
    JOIN pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname <> 'information_schema'
      AND n.nspname NOT LIKE 'pg_%'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f', 'i')
      AND c.relowner <> (SELECT oid FROM pg_roles WHERE rolname = 'koi_console')
  LOOP
    IF rel.relkind = 'S' THEN
      EXECUTE format('ALTER SEQUENCE %s OWNER TO koi_console', rel.obj);
    ELSIF rel.relkind = 'v' THEN
      EXECUTE format('ALTER VIEW %s OWNER TO koi_console', rel.obj);
    ELSIF rel.relkind = 'm' THEN
      EXECUTE format('ALTER MATERIALIZED VIEW %s OWNER TO koi_console', rel.obj);
    ELSIF rel.relkind = 'i' THEN
      EXECUTE format('ALTER INDEX %s OWNER TO koi_console', rel.obj);
    ELSIF rel.relkind = 'f' THEN
      EXECUTE format('ALTER FOREIGN TABLE %s OWNER TO koi_console', rel.obj);
    ELSE
      EXECUTE format('ALTER TABLE %s OWNER TO koi_console', rel.obj);
    END IF;
  END LOOP;

  GRANT USAGE, CREATE ON SCHEMA app TO koi_console;
  GRANT USAGE ON SCHEMA public TO koi_console;
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO koi_console;
  GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO koi_console;

  FOR dbname IN
    SELECT datname
    FROM pg_database
    WHERE datallowconn
      AND datname <> current_database()
  LOOP
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', dbname);
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM koi_console', dbname);
  END LOOP;

  EXECUTE format(
    'GRANT CONNECT, TEMP ON DATABASE %I TO koi_console',
    current_database()
  );
  EXECUTE format(
    'ALTER ROLE koi_console IN DATABASE %I SET search_path TO app, public',
    current_database()
  );

  IF current IS DISTINCT FROM expected THEN
    PERFORM set_config('log_statement', 'none', true);
    PERFORM set_config('log_min_error_statement', 'panic', true);
    EXECUTE format('ALTER ROLE koi_console PASSWORD %L', expected);
  END IF;
END
$console$;
"""


def console_role_password(pond_password: str) -> str:
    digest = hashlib.sha256(
        b"koicloud.console-role.v1\0" + pond_password.encode("utf-8")
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def scram_sha256_verifier(password: str, salt: bytes) -> str:
    salted = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _SCRAM_ITERATIONS,
    )
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    salt_b64 = base64.b64encode(salt).decode("ascii")
    stored_b64 = base64.b64encode(stored_key).decode("ascii")
    server_b64 = base64.b64encode(server_key).decode("ascii")
    return f"SCRAM-SHA-256${_SCRAM_ITERATIONS}:{salt_b64}${stored_b64}:{server_b64}"


def _salt_from_verifier(stored: str | None) -> bytes | None:
    if not stored:
        return None
    parts = stored.split("$")
    if len(parts) != 3 or parts[0] != "SCRAM-SHA-256":
        return None
    iteration_and_salt = parts[1].split(":", 1)
    if len(iteration_and_salt) != 2 or iteration_and_salt[0] != str(_SCRAM_ITERATIONS):
        return None
    try:
        salt = base64.b64decode(iteration_and_salt[1], validate=True)
    except ValueError:
        return None
    if len(salt) != _SALT_BYTES:
        return None
    return salt


def verifier_for(password: str, stored: str | None) -> str:
    """Reuse the pond's salt when it still matches this password.

    A fresh pond, or a password rotation, gets a new random salt. The salt
    lives in the stored SCRAM verifier, so the next check can rebuild it.
    """
    salt = _salt_from_verifier(stored)
    if salt is not None and stored is not None:
        candidate = scram_sha256_verifier(password, salt)
        if hmac.compare_digest(candidate, stored):
            return stored
    return scram_sha256_verifier(password, os.urandom(_SALT_BYTES))


_REPAIR_PROBE = """
SELECT
  EXISTS (
    SELECT 1 FROM pg_roles
    WHERE rolname = 'koi_console'
      AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
  )
  OR pg_has_role('pg_read_server_files', 'member')
  OR pg_has_role('pg_write_server_files', 'member')
  OR pg_has_role('pg_execute_server_program', 'member')
  OR EXISTS (
    SELECT 1
    FROM pg_namespace AS n
    JOIN pg_roles AS r ON r.oid = n.nspowner
    WHERE n.nspname <> 'information_schema'
      AND n.nspname NOT LIKE 'pg_%'
      AND r.rolname <> 'koi_console'
  )
  OR EXISTS (
    SELECT 1
    FROM pg_class AS c
    JOIN pg_namespace AS n ON n.oid = c.relnamespace
    JOIN pg_roles AS r ON r.oid = c.relowner
    WHERE n.nspname <> 'information_schema'
      AND n.nspname NOT LIKE 'pg_%'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f', 'i')
      AND r.rolname <> 'koi_console'
  )
  OR EXISTS (
    SELECT 1
    FROM pg_database AS d
    WHERE d.datallowconn
      AND d.datname <> current_database()
      AND (
        has_database_privilege('public', d.datname, 'CONNECT')
        OR has_database_privilege('koi_console', d.datname, 'CONNECT')
      )
  )
"""


async def console_needs_repair(conn: asyncpg.Connection) -> bool:
    """Read-only check. A clean pond does not take the setup lock."""
    return bool(await conn.fetchval(_REPAIR_PROBE))


async def ensure_console_role(conn: asyncpg.Connection, password: str) -> None:
    """Make koi_console match the console contract.

    Callers share one catalog row, so the lock is the write gate. A stored
    verifier that already matches means this transaction changes nothing.
    """
    async with conn.transaction():
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtext('koicloud.console-role.v1'))"
        )
        stored = await conn.fetchval(
            "SELECT rolpassword FROM pg_authid WHERE rolname = $1",
            CONSOLE_ROLE,
        )
        verifier = verifier_for(password, stored if isinstance(stored, str) else None)
        await conn.execute(
            "SELECT set_config('koicloud.console_verifier', $1, true)",
            verifier,
        )
        await conn.execute(_SETUP_SQL)
