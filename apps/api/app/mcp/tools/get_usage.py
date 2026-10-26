from __future__ import annotations

from typing import Any

from app.commands import usage as usage_commands
from app.mcp.context import require_mcp_actor
from app.mcp.server import _dump, mcp


@mcp.tool
async def get_usage(month: str | None = None) -> dict[str, Any]:
    return _dump(await usage_commands.get_usage(require_mcp_actor(), month))
