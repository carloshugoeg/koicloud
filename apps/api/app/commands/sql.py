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
from app.modules.ponds import PondService
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


async def _execute(connection: ConnectionOut, payload: RunSQLRequest) -> SQLResultResponse:
    started = time.perf_counter()
    try:
        conn = await asyncpg.connect(
            host=connection.host,
            port=connection.port,
            user=connection.username,
            password=connection.password,
            database=connection.database,
            timeout=10,
        )
    except (OSError, asyncpg.PostgresError) as exc:
        raise AppError(ErrorCode.NODE_UNAVAILABLE) from exc
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
