from __future__ import annotations

from typing import Any

from app.commands import backups as backup_commands
from app.commands import ponds as pond_commands
from app.mcp.context import require_mcp_actor
from app.mcp.server import _dump, mcp


@mcp.tool
async def list_backups(pond_name: str) -> dict[str, Any]:
    actor = require_mcp_actor()
    pond = await pond_commands.get_pond_by_name(actor, pond_name)
    return _dump(await backup_commands.list_backups(actor, pond.pond.id))
