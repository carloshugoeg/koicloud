from __future__ import annotations

from typing import Any
from uuid import UUID

from fastmcp import FastMCP

from app.commands import backups as backup_commands
from app.commands import confirmations as confirmation_commands
from app.commands import ponds as pond_commands
from app.commands import sql as sql_commands
from app.core.auth import AuthContext
from app.core.enums import AppSurface, SQLMode
from app.core.errors import AppError, ErrorCode
from app.mcp.context import require_mcp_actor
from app.mcp.prompt import SYSTEM_PROMPT
from app.schemas import (
    ConfirmationRequiredResponse,
    CreatePondRequest,
    RestoreBackupRequest,
    RunSQLRequest,
)

mcp = FastMCP("KoiCloud", instructions=SYSTEM_PROMPT)


def _dump(result: Any) -> dict[str, Any]:
    if isinstance(result, ConfirmationRequiredResponse):
        return result.model_dump(mode="json")
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return dict(result)


def _actor_for_tool(tool_name: str) -> AuthContext:
    """Enforce pond-temp allowlists on every transport (JSON-RPC and Streamable HTTP)."""
    actor = require_mcp_actor()
    if actor.allowed_tools is not None and tool_name not in actor.allowed_tools:
        raise AppError(ErrorCode.AGENT_DISABLED)
    return actor


@mcp.tool
async def whoami() -> dict[str, Any]:
    actor = _actor_for_tool("whoami")
    return {"user_id": actor.user_id, "email": actor.email, "role": actor.role.value}


@mcp.tool
async def list_ponds() -> dict[str, Any]:
    return _dump(await pond_commands.list_ponds(_actor_for_tool("list_ponds")))


@mcp.tool
async def get_pond(name: str) -> dict[str, Any]:
    return _dump(await pond_commands.get_pond_by_name(_actor_for_tool("get_pond"), name))


@mcp.tool
async def create_pond(name: str, engine_version: str = "16") -> dict[str, Any]:
    actor = _actor_for_tool("create_pond")
    result = await pond_commands.create_pond(
        CreatePondRequest(name=name, engine_version=engine_version),
        actor=actor,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def delete_pond(name: str) -> dict[str, Any]:
    actor = _actor_for_tool("delete_pond")
    pond = await pond_commands.get_pond_by_name(actor, name)
    result = await pond_commands.delete_pond(
        actor,
        pond.pond.id,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def stop_pond(name: str) -> dict[str, Any]:
    actor = _actor_for_tool("stop_pond")
    pond = await pond_commands.get_pond_by_name(actor, name)
    result = await pond_commands.stop_pond(
        actor,
        pond.pond.id,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def start_pond(name: str) -> dict[str, Any]:
    actor = _actor_for_tool("start_pond")
    pond = await pond_commands.get_pond_by_name(actor, name)
    result = await pond_commands.start_pond(
        actor,
        pond.pond.id,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def restore_backup(pond_name: str, backup_id: str) -> dict[str, Any]:
    actor = _actor_for_tool("restore_backup")
    pond = await pond_commands.get_pond_by_name(actor, pond_name)
    result = await backup_commands.restore_backup(
        pond.pond.id,
        RestoreBackupRequest(backup_id=UUID(backup_id)),
        actor=actor,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def run_sql(pond_name: str, query: str, mode: str = "read") -> dict[str, Any]:
    actor = _actor_for_tool("run_sql")
    pond = await pond_commands.get_pond_by_name(actor, pond_name)
    result = await sql_commands.run_sql(
        pond.pond.id,
        RunSQLRequest(query=query, mode=SQLMode(mode)),
        actor=actor,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def confirm_action(
    token: str,
    query: str | None = None,
    mode: str | None = None,
    pond_id: str | None = None,
    action: str | None = None,
    pond_token_id: str | None = None,
) -> dict[str, Any]:
    # Spec: client extras never override the stored proposal; accept and drop them.
    _ = (query, mode, pond_id, action, pond_token_id)
    actor = _actor_for_tool("confirm_action")
    return await confirmation_commands.confirm_action(token, actor=actor)


@mcp.tool
async def cancel_confirmation(token: str) -> dict[str, str]:
    actor = _actor_for_tool("cancel_confirmation")
    await confirmation_commands.discard_pending_confirmation(token, actor=actor)
    return {"status": "discarded"}
