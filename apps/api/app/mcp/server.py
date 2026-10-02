from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.commands import confirmations as confirmation_commands
from app.commands import ponds as pond_commands
from app.core.enums import AppSurface
from app.mcp.context import require_mcp_actor
from app.mcp.prompt import SYSTEM_PROMPT
from app.schemas import ConfirmationRequiredResponse, CreatePondRequest

mcp = FastMCP("KoiCloud", instructions=SYSTEM_PROMPT)


def _dump(result: Any) -> dict[str, Any]:
    if isinstance(result, ConfirmationRequiredResponse):
        return result.model_dump(mode="json")
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return dict(result)


@mcp.tool
async def whoami() -> dict[str, Any]:
    actor = require_mcp_actor()
    return {"user_id": actor.user_id, "email": actor.email, "role": actor.role.value}


@mcp.tool
async def list_ponds() -> dict[str, Any]:
    return _dump(await pond_commands.list_ponds(require_mcp_actor()))


@mcp.tool
async def get_pond(name: str) -> dict[str, Any]:
    return _dump(await pond_commands.get_pond_by_name(require_mcp_actor(), name))


@mcp.tool
async def create_pond(name: str, engine_version: str = "16") -> dict[str, Any]:
    actor = require_mcp_actor()
    result = await pond_commands.create_pond(
        CreatePondRequest(name=name, engine_version=engine_version),
        actor=actor,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def delete_pond(name: str) -> dict[str, Any]:
    actor = require_mcp_actor()
    pond = await pond_commands.get_pond_by_name(actor, name)
    result = await pond_commands.delete_pond(
        actor,
        pond.pond.id,
        surface=AppSurface.MCP,
    )
    return _dump(result)


@mcp.tool
async def confirm_action(token: str) -> dict[str, Any]:
    return await confirmation_commands.confirm_action(token)


@mcp.tool
async def cancel_confirmation(token: str) -> dict[str, str]:
    await confirmation_commands.discard_pending_confirmation(token)
    return {"status": "discarded"}
