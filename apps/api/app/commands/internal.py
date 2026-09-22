from __future__ import annotations

from app.schemas import (
    ClaimJobRequest,
    ClaimJobResponse,
    CompleteJobRequest,
    NodeSampleUpload,
    OkResponse,
)


async def heartbeat(_: object) -> OkResponse:
    return OkResponse(ok=True)


async def claim_job(_: ClaimJobRequest) -> ClaimJobResponse:
    return ClaimJobResponse.example()


async def complete_job(_: str, __: CompleteJobRequest) -> None:
    return None


async def ingest_samples(_: list[NodeSampleUpload]) -> OkResponse:
    return OkResponse(ok=True)
