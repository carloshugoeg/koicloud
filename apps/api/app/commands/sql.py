from __future__ import annotations

from uuid import UUID

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.enums import AppSurface, SQLMode
from app.schemas import (
    ConfirmationRequiredResponse,
    RunSQLRequest,
    SQLHistoryResponse,
    SQLResultResponse,
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
        return build_confirmation(
            action="run_sql_write",
            summary=(
                f"Se ejecutará SQL en modo write sobre el pond '{pond_id}' para {actor.email}. "
                "Expira en 5 min."
            ),
        )
    return SQLResultResponse.example()


async def list_sql_history(_: AuthContext, __: UUID) -> SQLHistoryResponse:
    return SQLHistoryResponse.example()
