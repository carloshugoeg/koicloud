from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.auth import AuthContext
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


async def _dispatch_jsonrpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
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
        return {"status": "error", "message": "tool name required"}

    call_result = await mcp.call_tool(tool_name, arguments)
    data = getattr(call_result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(call_result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    return {"result": data if data is not None else str(call_result)}
