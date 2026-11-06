from __future__ import annotations

import base64
import hashlib
import hmac
import os

_SCRAM_ITERATIONS = 4096
_SALT_BYTES = 16
# Same-process memory of a salt we already generated. The driver also passes
# the verifier stored in pg_authid, which wins after a restart.
_pond_salts: dict[tuple[str, str], bytes] = {}

# Same body as apps/api/app/modules/ponds/console_role.py.
_SQL = """
BEGIN;
SELECT pg_advisory_xact_lock(hashtext('koicloud.console-role.v1'));
SELECT set_config('koicloud.console_verifier', :'console_verifier', true);
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
COMMIT;
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


def _salt_key(database: str, password: str) -> tuple[str, str]:
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return database, digest


def verifier_for(password: str, stored: str | None, *, database: str) -> str:
    salt = _salt_from_verifier(stored)
    key = _salt_key(database, password)
    if salt is not None and stored is not None:
        candidate = scram_sha256_verifier(password, salt)
        if hmac.compare_digest(candidate, stored):
            _pond_salts[key] = salt
            return stored
    if stored is None and key in _pond_salts:
        return scram_sha256_verifier(password, _pond_salts[key])
    salt = os.urandom(_SALT_BYTES)
    _pond_salts[key] = salt
    return scram_sha256_verifier(password, salt)


def console_role_environment(
    database: str,
    pond_password: str,
    stored: str | None = None,
) -> dict[str, str]:
    return {
        "PGPASSWORD": pond_password,
        "KOI_DB": database,
        "KOI_CONSOLE_VERIFIER": verifier_for(
            console_role_password(pond_password),
            stored,
            database=database,
        ),
        "KOI_SQL": _SQL,
    }


def console_role_argv() -> list[str]:
    return [
        "sh",
        "-c",
        (
            "printf '%s\\n' \"$KOI_SQL\" | psql -U postgres -d \"$KOI_DB\" "
            "-v ON_ERROR_STOP=1 -v console_verifier=\"$KOI_CONSOLE_VERIFIER\" "
            "-v db=\"$KOI_DB\" -f -"
        ),
    ]
