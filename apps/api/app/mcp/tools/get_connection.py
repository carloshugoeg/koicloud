from __future__ import annotations

from typing import Any

from app.commands import ponds as pond_commands
from app.mcp.server import _actor_for_tool, _dump, mcp


@mcp.tool
async def get_connection(name: str) -> dict[str, Any]:
    actor = _actor_for_tool("get_connection")
    pond = await pond_commands.get_pond_by_name(actor, name)
    return _dump(await pond_commands.get_connection(actor, pond.pond.id))
