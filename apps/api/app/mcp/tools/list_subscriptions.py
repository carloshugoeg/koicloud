from __future__ import annotations

from typing import Any

from app.commands import billing as billing_commands
from app.mcp.server import _actor_for_tool, _dump, mcp


@mcp.tool
async def list_subscriptions() -> dict[str, Any]:
    return _dump(
        await billing_commands.list_my_subscriptions(_actor_for_tool("list_subscriptions"))
    )
