from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import AuthContext, get_mcp_user
from app.schemas import JsonRpcRequest, JsonRpcResponse, MCPInfoResponse

from .prompt import SYSTEM_PROMPT

router = APIRouter()


@router.get(
    "",
    response_model=MCPInfoResponse,
    operation_id="mcp_info",
    tags=["mcp"],
)
async def mcp_info(_: Annotated[AuthContext, Depends(get_mcp_user)]) -> MCPInfoResponse:
    info = MCPInfoResponse.example()
    info.prompt_summary = SYSTEM_PROMPT.strip().splitlines()[0]
    return info


@router.post(
    "",
    response_model=JsonRpcResponse,
    operation_id="mcp_jsonrpc",
    tags=["mcp"],
)
async def mcp_jsonrpc(
    payload: JsonRpcRequest,
    _: Annotated[AuthContext, Depends(get_mcp_user)],
) -> JsonRpcResponse:
    return JsonRpcResponse(
        jsonrpc="2.0",
        id=payload.id,
        result={
            "status": "ok",
            "message": "MCP skeleton ready",
            "method": payload.method,
        },
        error=None,
    )
