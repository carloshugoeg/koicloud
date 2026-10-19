from app.mcp import tools as _read_tools  # noqa: F401
from app.mcp.router import router
from app.mcp.server import mcp

__all__ = ["mcp", "router"]
