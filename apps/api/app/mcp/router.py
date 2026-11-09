from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.auth import AuthContext
from app.core.errors import AppError, ErrorCode
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
    "get_usage",
    "list_tables",
]
MUTABLE_TOOLS = [
    "create_pond",
    "delete_pond",
    "stop_pond",
    "start_pond",
    "restore_backup",
    "run_sql",
    "confirm_action",
    "cancel_confirmation",
]


def _tools_for_actor(actor: AuthContext) -> tuple[list[str], list[str]]:
    if actor.allowed_tools is None:
        return list(READ_ONLY_TOOLS), list(MUTABLE_TOOLS)
    allowed = actor.allowed_tools
    return (
        [name for name in READ_ONLY_TOOLS if name in allowed],
        [name for name in MUTABLE_TOOLS if name in allowed],
    )


def _assert_tool_allowed(actor: AuthContext, tool_name: str) -> None:
    if actor.allowed_tools is None:
        return
    if tool_name not in actor.allowed_tools:
        raise AppError(ErrorCode.AGENT_DISABLED)


@router.get(
    "",
    response_model=MCPInfoResponse,
    operation_id="mcp_info",
    tags=["mcp"],
)
async def mcp_info(actor: Annotated[AuthContext, Depends(mcp_gate_dependency)]) -> MCPInfoResponse:
    read_only, mutable = _tools_for_actor(actor)
    return MCPInfoResponse(
        enabled=True,
        endpoint="/mcp",
        read_only_tools=read_only,
        mutable_tools=mutable,
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
        result = await _dispatch_jsonrpc(actor, payload.method, payload.params or {})
    finally:
        clear_mcp_actor()
    return JsonRpcResponse(jsonrpc="2.0", id=payload.id, result=result, error=None)


async def _dispatch_jsonrpc(
    actor: AuthContext, method: str, params: dict[str, Any]
) -> dict[str, Any]:
    if method in {"tools/list", "list_tools"}:
        tools = await mcp.list_tools()
        if actor.allowed_tools is not None:
            tools = [tool for tool in tools if tool.name in actor.allowed_tools]
        return {"tools": [{"name": tool.name, "description": tool.description} for tool in tools]}

    tool_name = method
    arguments = params
    if method in {"tools/call", "call_tool"}:
        tool_name = str(params.get("name") or params.get("tool") or "")
        raw_args = params.get("arguments") or params.get("params") or {}
        arguments = raw_args if isinstance(raw_args, dict) else {}

    if not tool_name:
        return {"status": "error", "message": "tool name required"}

    _assert_tool_allowed(actor, tool_name)
    try:
        call_result = await mcp.call_tool(tool_name, arguments)
    except Exception as exc:
        # FastMCP wraps AppError in ToolError; surface the catalog code in the
        # JSON-RPC result (same shape as confirmation_required) so callers see
        # sql_error / node_unavailable / pond_not_found without a 500.
        cause = exc.__cause__ if isinstance(exc.__cause__, AppError) else None
        if cause is None and isinstance(exc, AppError):
            cause = exc
        if cause is not None:
            return {"code": cause.code.value, "message": cause.message, "status": "error"}
        raise
    data = getattr(call_result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(call_result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    return {"result": data if data is not None else str(call_result)}
