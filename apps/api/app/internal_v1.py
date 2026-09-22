from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status

from app.commands import internal as internal_commands
from app.core.auth import NodeContext, get_node_identity
from app.schemas import (
    ClaimJobRequest,
    ClaimJobResponse,
    CompleteJobRequest,
    HeartbeatRequest,
    NodeSampleUpload,
    OkResponse,
)

router = APIRouter()


@router.post(
    "/heartbeat",
    response_model=OkResponse,
    operation_id="internal_heartbeat",
    tags=["internal"],
)
async def heartbeat(
    payload: HeartbeatRequest,
    _: Annotated[NodeContext, Depends(get_node_identity)],
) -> OkResponse:
    return await internal_commands.heartbeat(payload)


@router.post(
    "/jobs/claim",
    response_model=ClaimJobResponse,
    operation_id="internal_claim_job",
    tags=["internal"],
    responses={204: {"description": "No hay jobs disponibles"}},
)
async def claim_job(
    payload: ClaimJobRequest,
    _: Annotated[NodeContext, Depends(get_node_identity)],
) -> ClaimJobResponse:
    return await internal_commands.claim_job(payload)


@router.post(
    "/jobs/{job_id}/complete",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="internal_complete_job",
    tags=["internal"],
)
async def complete_job(
    job_id: str,
    payload: CompleteJobRequest,
    _: Annotated[NodeContext, Depends(get_node_identity)],
) -> Response:
    await internal_commands.complete_job(job_id, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/samples",
    response_model=OkResponse,
    operation_id="internal_ingest_samples",
    tags=["internal"],
)
async def ingest_samples(
    payload: Annotated[
        list[NodeSampleUpload],
        Body(examples=[NodeSampleUpload.example_data()]),
    ],
    _: Annotated[NodeContext, Depends(get_node_identity)],
) -> OkResponse:
    return await internal_commands.ingest_samples(payload)
