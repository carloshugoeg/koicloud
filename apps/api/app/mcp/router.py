from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastmcp.exceptions import NotFoundError, ToolError, ValidationError

from app.core.auth import AuthContext
from app.core.errors import ERROR_CATALOG, AppError, ErrorCode
from app.mcp.context import clear_mcp_actor, set_mcp_actor
from app.mcp.gate import mcp_gate_dependency
from app.mcp.prompt import SYSTEM_PROMPT
from app.mcp.server import mcp
from app.schemas import JsonRpcRequest, JsonRpcResponse, MCPInfoResponse

router = APIRouter()

READ_ONLY_TOOLS = [
    "whoami",
    "list_ponds",
    "get_pond",
    "get_connection",
    "list_subscriptions",
    "list_backups",
]
MUTABLE_TOOLS = [
    "create_pond",
    "delete_pond",
    "restore_backup",
    "run_sql",
    "confirm_action",
    "cancel_confirmation",
]


@router.get(
    "",
    response_model=MCPInfoResponse,
    operation_id="mcp_info",
    tags=["mcp"],
)
async def mcp_info(_: Annotated[AuthContext, Depends(mcp_gate_dependency)]) -> MCPInfoResponse:
    return MCPInfoResponse(
        enabled=True,
        endpoint="/mcp",
        read_only_tools=READ_ONLY_TOOLS,
        mutable_tools=MUTABLE_TOOLS,
        prompt_summary=SYSTEM_PROMPT.strip().splitlines()[0],
    )


@router.post(
    "",
    response_model=JsonRpcResponse,
    operation_id="mcp_jsonrpc",
    tags=["mcp"],
)
async def mcp_jsonrpc(
    payload: JsonRpcRequest,
    actor: Annotated[AuthContext, Depends(mcp_gate_dependency)],
) -> JsonRpcResponse:
    set_mcp_actor(actor)
    try:
        result = await _dispatch_jsonrpc(payload.method, payload.params or {})
    finally:
        clear_mcp_actor()
    return JsonRpcResponse(jsonrpc="2.0", id=payload.id, result=result, error=None)


def _tool_error_result(name: str, code: ErrorCode, message: str | None = None) -> dict[str, Any]:
    """MCP tools/call error payload aligned with lib/errors.ts catalog codes."""
    text = message or ERROR_CATALOG[code].message
    return {
        "content": [{"type": "text", "text": f"Error calling tool '{name}': {text}"}],
        "structuredContent": {"code": code.value, "message": text},
        "isError": True,
        "code": code.value,
        "message": text,
    }


def _app_error_from(exc: BaseException) -> AppError | None:
    """Unwrap AppError that FastMCP nests under ToolError.__cause__."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        if isinstance(current, AppError):
            return current
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return None


async def _dispatch_jsonrpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
    # MCP session handshake over the OpenAPI JSON-RPC surface (Accept: application/json).
    # Streamable HTTP clients use FastMCP via McpHybridASGI instead.
    if method.startswith("notifications/"):
        return {}
    if method == "ping":
        return {}
    if method == "initialize":
        from app.core.config import get_settings

        version = params.get("protocolVersion")
        protocol = version if isinstance(version, str) and version else "2024-11-05"
        settings = get_settings()
        return {
            "protocolVersion": protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "KoiCloud", "version": settings.app_version},
        }

    if method in {"tools/list", "list_tools"}:
        tools = await mcp.list_tools()
        return {"tools": [{"name": tool.name, "description": tool.description} for tool in tools]}

    tool_name = method
    arguments = params
    if method in {"tools/call", "call_tool"}:
        tool_name = str(params.get("name") or params.get("tool") or "")
        raw_args = params.get("arguments") or params.get("params") or {}
        arguments = raw_args if isinstance(raw_args, dict) else {}

    if not tool_name:
        return _tool_error_result("tools/call", ErrorCode.INTERNAL_ERROR, "tool name required")

    try:
        call_result = await mcp.call_tool(tool_name, arguments)
    except NotFoundError:
        return _tool_error_result(
            tool_name,
            ErrorCode.INTERNAL_ERROR,
            f"unknown tool '{tool_name}'",
        )
    except ValidationError as exc:
        return _tool_error_result(tool_name, ErrorCode.INTERNAL_ERROR, str(exc))
    except AppError as exc:
        return _tool_error_result(tool_name, exc.code, exc.message)
    except ToolError as exc:
        # FastMCP wraps tool body exceptions as ToolError; keep catalog codes.
        nested = _app_error_from(exc)
        if nested is not None:
            return _tool_error_result(tool_name, nested.code, nested.message)
        return _tool_error_result(tool_name, ErrorCode.INTERNAL_ERROR, str(exc))

    data = getattr(call_result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(call_result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    return {"result": data if data is not None else str(call_result)}
