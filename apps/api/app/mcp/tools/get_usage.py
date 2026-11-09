from __future__ import annotations

from typing import Any

from app.commands import usage as usage_commands
from app.mcp.server import _actor_for_tool, _dump, mcp


@mcp.tool
async def get_usage(month: str | None = None) -> dict[str, Any]:
    return _dump(await usage_commands.get_usage(_actor_for_tool("get_usage"), month))
