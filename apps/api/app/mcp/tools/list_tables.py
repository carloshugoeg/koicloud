from __future__ import annotations

from typing import Any
from uuid import UUID

from app.commands import sql as sql_commands
from app.mcp.server import _actor_for_tool, _dump, mcp


@mcp.tool
async def list_tables(pond_id: str) -> dict[str, Any]:
    actor = _actor_for_tool("list_tables")
    return _dump(await sql_commands.get_pond_schema(actor, UUID(pond_id)))
