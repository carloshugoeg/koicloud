from __future__ import annotations

import logging
import time
from uuid import UUID

import asyncpg

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface, SQLMode
from app.core.errors import AppError, ErrorCode
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
    except _AUTH_FAILURES:
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
) -> SQLResultResponse | ConfirmationRequiredResponse:
    if payload.mode == SQLMode.WRITE and surface in {AppSurface.CLI, AppSurface.MCP} and not confirm_token:
        return await build_confirmation(
            actor=actor,
            action="run_sql_write",
            summary=(
                f"Se ejecutará SQL en modo write sobre el pond '{pond_id}' para {actor.email}. "
                "Expira en 5 min."
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


async def list_sql_history(actor: AuthContext, pond_id: UUID) -> SQLHistoryResponse:
    async with SessionLocal() as session:
        return await SqlConsoleService(session).list_for_actor(
            actor,
            pond_id,
            limit=get_settings().default_limit,
            cursor=None,
        )
