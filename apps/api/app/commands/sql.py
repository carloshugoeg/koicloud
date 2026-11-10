from __future__ import annotations

import logging
import time
from collections import defaultdict
from uuid import UUID

import asyncpg

from app.commands import build_confirmation
from app.commands.temp_sql_confirmation import (
    TempSqlDispatchGrant,
    assert_grant_matches_request,
    is_temp_actor,
    lock_live_pond_token,
)
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface, PondObservedState, SQLMode
from app.core.errors import AppError, ErrorCode
from app.core.time import utc_now
from app.modules.pond_tokens.service import phase_of
from app.modules.ponds import (
    CONSOLE_ROLE,
    PondService,
    console_needs_repair,
    console_role_password,
    ensure_console_role,
)
from app.modules.sql_console import HistoryWrite, SqlConsoleService
from app.schemas import (
    ConfirmationRequiredResponse,
    ConnectionOut,
    PondColumnOut,
    PondSchemaResponse,
    PondTableOut,
    RunSQLRequest,
    SQLHistoryResponse,
    SQLResultResponse,
)

logger = logging.getLogger(__name__)

ROW_CAP = 1000
STATEMENT_TIMEOUT = "10s"
_USER_SQL_ERRORS = (
    asyncpg.exceptions.SyntaxOrAccessError,
    asyncpg.exceptions.DataError,
    asyncpg.exceptions.IntegrityConstraintViolationError,
    asyncpg.exceptions.RaiseError,
)

_SCHEMA_TABLES_SQL = """
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  GREATEST(COALESCE(c.reltuples, 0), 0)::bigint AS estimated_rows
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
  AND n.nspname NOT LIKE 'pg_temp%'
ORDER BY n.nspname, c.relname
"""

_SCHEMA_COLUMNS_SQL = """
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  a.attname AS column_name,
  pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
  NOT a.attnotnull AS nullable,
  pg_catalog.pg_get_expr(ad.adbin, ad.adrelid) AS column_default
FROM pg_catalog.pg_attribute a
JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_catalog.pg_attrdef ad
  ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
WHERE a.attnum > 0
  AND NOT a.attisdropped
  AND c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
  AND n.nspname NOT LIKE 'pg_temp%'
ORDER BY n.nspname, c.relname, a.attnum
"""


def _cell(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, bytes | memoryview):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


_AUTH_FAILURES = (
    asyncpg.InvalidPasswordError,
    asyncpg.InvalidAuthorizationSpecificationError,
)
# Sibling repair REVOKE CONNECT yields 42501, not an auth failure.
_CONSOLE_CONNECT_DENIED = (asyncpg.exceptions.InsufficientPrivilegeError,)


async def _open(connection: ConnectionOut, *, user: str, password: str) -> asyncpg.Connection:
    return await asyncpg.connect(
        host=connection.host,
        port=connection.port,
        user=user,
        password=password,
        database=connection.database,
        timeout=10,
    )


async def _connect(connection: ConnectionOut, *, user: str, password: str) -> asyncpg.Connection:
    try:
        return await _open(connection, user=user, password=password)
    except (OSError, asyncpg.PostgresError) as exc:
        raise AppError(ErrorCode.NODE_UNAVAILABLE) from exc


async def _repair_console_role(connection: ConnectionOut, console_password: str) -> asyncpg.Connection:
    admin = await _connect(
        connection,
        user=connection.username,
        password=connection.password,
    )
    try:
        await ensure_console_role(admin, console_password)
    except asyncpg.PostgresError as exc:
        logger.warning("console role repair failed sqlstate=%s", exc.sqlstate)
        raise AppError(ErrorCode.INTERNAL_ERROR) from None
    finally:
        await admin.close()
    return await _connect(connection, user=CONSOLE_ROLE, password=console_password)


async def _open_console(connection: ConnectionOut, console_password: str) -> asyncpg.Connection:
    try:
        conn = await _open(connection, user=CONSOLE_ROLE, password=console_password)
    except (*_AUTH_FAILURES, *_CONSOLE_CONNECT_DENIED):
        return await _repair_console_role(connection, console_password)
    except (OSError, asyncpg.PostgresError) as exc:
        raise AppError(ErrorCode.NODE_UNAVAILABLE) from exc
    if await console_needs_repair(conn):
        await conn.close()
        return await _repair_console_role(connection, console_password)
    return conn


async def _execute(connection: ConnectionOut, payload: RunSQLRequest) -> SQLResultResponse:
    started = time.perf_counter()
    console_password = console_role_password(connection.password)
    conn = await _open_console(connection, console_password)
    try:
        await conn.execute(
            "SELECT set_config('statement_timeout', $1, false)",
            STATEMENT_TIMEOUT,
        )
        readonly = payload.mode == SQLMode.READ
        async with conn.transaction(readonly=readonly):
            prepared = await conn.prepare(payload.query)
            columns = [attribute.name for attribute in prepared.get_attributes()]
            rows: list[list[object]] = []
            truncated = False
            async for record in prepared.cursor(prefetch=ROW_CAP + 1):
                if len(rows) == ROW_CAP:
                    truncated = True
                    break
                rows.append([_cell(value) for value in record])
    except asyncpg.exceptions.ReadOnlySQLTransactionError as exc:
        raise AppError(ErrorCode.SQL_READONLY_VIOLATION) from exc
    except asyncpg.exceptions.QueryCanceledError as exc:
        raise AppError(ErrorCode.SQL_TIMEOUT) from exc
    except asyncpg.exceptions.PostgresConnectionError as exc:
        raise AppError(ErrorCode.NODE_UNAVAILABLE) from exc
    except _USER_SQL_ERRORS as exc:
        logger.warning("pond sql rejected", exc_info=exc)
        raise AppError(ErrorCode.SQL_ERROR) from exc
    except asyncpg.PostgresError as exc:
        logger.warning("pond sql failed", exc_info=exc)
        raise AppError(ErrorCode.INTERNAL_ERROR) from exc
    finally:
        await conn.close()

    duration_ms = max(0, int((time.perf_counter() - started) * 1000))
    return SQLResultResponse(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        duration_ms=duration_ms,
        truncated=truncated,
    )


async def run_sql(
    pond_id: UUID,
    payload: RunSQLRequest,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
    temp_grant: TempSqlDispatchGrant | None = None,
) -> SQLResultResponse | ConfirmationRequiredResponse:
    if payload.mode == SQLMode.WRITE and surface in {AppSurface.CLI, AppSurface.MCP}:
        if is_temp_actor(actor):
            # Truthy confirm_token is not authorization for temp actors.
            if temp_grant is None:
                return await build_confirmation(
                    actor=actor,
                    action="run_sql_write",
                    summary=(
                        f"Se ejecutará SQL en modo write sobre el pond '{pond_id}' "
                        f"para {actor.email}."
                    ),
                    payload={
                        "pond_id": str(pond_id),
                        "request": payload.model_dump(mode="json"),
                    },
                )
            assert_grant_matches_request(
                temp_grant,
                pond_id=pond_id,
                query=payload.query,
                mode=payload.mode.value,
            )
            return await _execute_temp_admitted(
                pond_id, payload, actor=actor, grant=temp_grant
            )
        if not confirm_token:
            return await build_confirmation(
                actor=actor,
                action="run_sql_write",
                summary=(
                    f"Se ejecutará SQL en modo write sobre el pond '{pond_id}' "
                    f"para {actor.email}. Expira en 5 min."
                ),
                payload={"pond_id": str(pond_id), "request": payload.model_dump(mode="json")},
            )

    async with SessionLocal() as session:
        connection = await PondService(session, get_settings()).connection_for_owned(actor, pond_id)
        result = await _execute(connection, payload)
        await SqlConsoleService(session).record(
            HistoryWrite(
                user_id=UUID(actor.user_id),
                pond_id=pond_id,
                query=payload.query,
                mode=payload.mode,
                row_count=result.row_count,
                duration_ms=result.duration_ms,
            )
        )
        await session.commit()
    return result


async def _execute_temp_admitted(
    pond_id: UUID,
    payload: RunSQLRequest,
    *,
    actor: AuthContext,
    grant: TempSqlDispatchGrant,
) -> SQLResultResponse:
    """Re-lock credential, recheck deadline, retain lock across SQL execution."""
    if actor.pond_token_id is None:
        raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
    async with SessionLocal() as session:
        token_row = await lock_live_pond_token(
            session,
            pond_token_id=UUID(actor.pond_token_id),
            actor=actor,
        )
        if token_row.id != grant.pond_token_id or token_row.pond_id != pond_id:
            raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)
        connection = await PondService(session, get_settings()).connection_for_owned(
            actor, pond_id
        )
        await session.refresh(token_row)
        if phase_of(token_row, now=utc_now()) in {"expired", "revoked"}:
            raise AppError(ErrorCode.AGENT_BAD_CREDENTIALS)
        result = await _execute(connection, payload)
        await SqlConsoleService(session).record(
            HistoryWrite(
                user_id=UUID(actor.user_id),
                pond_id=pond_id,
                query=payload.query,
                mode=payload.mode,
                row_count=result.row_count,
                duration_ms=result.duration_ms,
            )
        )
        await session.commit()
    return result


async def list_sql_history(actor: AuthContext, pond_id: UUID) -> SQLHistoryResponse:
    async with SessionLocal() as session:
        return await SqlConsoleService(session).list_for_actor(
            actor,
            pond_id,
            limit=get_settings().default_limit,
            cursor=None,
        )


async def _fetch_pond_schema(connection: ConnectionOut) -> PondSchemaResponse:
    console_password = console_role_password(connection.password)
    conn = await _open_console(connection, console_password)
    try:
        await conn.execute(
            "SELECT set_config('statement_timeout', $1, false)",
            STATEMENT_TIMEOUT,
        )
        async with conn.transaction(readonly=True):
            table_rows = await conn.fetch(_SCHEMA_TABLES_SQL)
            column_rows = await conn.fetch(_SCHEMA_COLUMNS_SQL)
    except asyncpg.exceptions.QueryCanceledError as exc:
        raise AppError(ErrorCode.SQL_TIMEOUT) from exc
    except asyncpg.exceptions.PostgresConnectionError as exc:
        raise AppError(ErrorCode.NODE_UNAVAILABLE) from exc
    except _USER_SQL_ERRORS as exc:
        logger.warning("pond schema rejected", exc_info=exc)
        raise AppError(ErrorCode.SQL_ERROR) from exc
    except asyncpg.PostgresError as exc:
        logger.warning("pond schema failed", exc_info=exc)
        raise AppError(ErrorCode.INTERNAL_ERROR) from exc
    finally:
        await conn.close()

    columns_by_table: dict[tuple[str, str], list[PondColumnOut]] = defaultdict(list)
    for row in column_rows:
        key = (row["schema_name"], row["table_name"])
        columns_by_table[key].append(
            PondColumnOut(
                name=row["column_name"],
                type=row["data_type"],
                nullable=bool(row["nullable"]),
                default=row["column_default"],
            )
        )

    tables = [
        PondTableOut(
            name=f"{row['schema_name']}.{row['table_name']}",
            estimated_rows=int(row["estimated_rows"]),
            columns=columns_by_table[(row["schema_name"], row["table_name"])],
        )
        for row in table_rows
    ]
    return PondSchemaResponse(tables=tables)


async def get_pond_schema(actor: AuthContext, pond_id: UUID) -> PondSchemaResponse:
    async with SessionLocal() as session:
        service = PondService(session, get_settings())
        _pond, status = await service.get_owned(actor, pond_id)
        if status.observed_state != PondObservedState.RUNNING:
            raise AppError(
                ErrorCode.POND_BUSY,
                message="El pond no está en ejecución",
            )
        connection = await service.connection_for_owned(actor, pond_id)
    return await _fetch_pond_schema(connection)
