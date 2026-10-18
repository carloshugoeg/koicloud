from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands import sql as sql_commands
from app.core.auth import AuthContext, get_current_user
from app.core.db import get_session
from app.core.deps import PaginationParams, get_confirmation_token, get_surface, pagination_params
from app.core.enums import AppSurface
from app.modules.sql_console.service import HistoryCursor, SqlConsoleService
from app.schemas import (
    ConfirmationRequiredResponse,
    RunSQLRequest,
    SQLHistoryResponse,
    SQLResultResponse,
)

router = APIRouter()


def _render(
    payload: SQLResultResponse | ConfirmationRequiredResponse,
    *,
    success_status: int,
) -> Response:
    if isinstance(payload, ConfirmationRequiredResponse):
        return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))
    return JSONResponse(status_code=success_status, content=payload.model_dump(mode="json"))


def parse_history_cursor(raw: str | None) -> HistoryCursor | None:
    if raw is None:
        return None
    stamp, separator, row_id = raw.partition("|")
    if not separator:
        raise HTTPException(status_code=422, detail="cursor inválido")
    try:
        return HistoryCursor(executed_at=datetime.fromisoformat(stamp), row_id=UUID(row_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="cursor inválido") from exc


@router.post(
    "/ponds/{pond_id}/sql",
    operation_id="sql_console_run_sql",
    tags=["sql"],
)
async def run_sql(
    pond_id: UUID,
    payload: RunSQLRequest,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await sql_commands.run_sql(
        pond_id,
        payload,
        actor=actor,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_200_OK)


@router.get(
    "/ponds/{pond_id}/sql/history",
    response_model=SQLHistoryResponse,
    operation_id="sql_console_list_history",
    tags=["sql"],
)
async def list_sql_history(
    pond_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
) -> SQLHistoryResponse:
    return await SqlConsoleService(session).list_for_actor(
        actor,
        pond_id,
        limit=pagination.limit,
        cursor=parse_history_cursor(pagination.cursor),
    )
