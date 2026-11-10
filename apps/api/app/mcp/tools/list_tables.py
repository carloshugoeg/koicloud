from __future__ import annotations

from typing import Any
from uuid import UUID

from app.commands import sql as sql_commands
from app.mcp.context import require_mcp_actor
from app.mcp.server import _dump, mcp


@mcp.tool
async def list_tables(pond_id: str) -> dict[str, Any]:
    actor = require_mcp_actor()
    return _dump(await sql_commands.get_pond_schema(actor, UUID(pond_id)))
