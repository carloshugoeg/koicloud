from __future__ import annotations

from typing import Any

from app.commands import billing as billing_commands
from app.mcp.context import require_mcp_actor
from app.mcp.server import _dump, mcp


@mcp.tool
async def list_subscriptions() -> dict[str, Any]:
    return _dump(await billing_commands.list_my_subscriptions(require_mcp_actor()))
