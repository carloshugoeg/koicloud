from __future__ import annotations

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.jobs.service import JobService
from app.modules.metering.service import MeteringService
from app.schemas import (
    ClaimJobRequest,
    ClaimJobResponse,
    CompleteJobRequest,
    HeartbeatRequest,
    NodeSampleUpload,
    OkResponse,
)


async def heartbeat(payload: HeartbeatRequest) -> OkResponse:
    async with SessionLocal() as session:
        settings = get_settings()
        await JobService(session, settings).heartbeat()
        await MeteringService(session, settings).ingest_heartbeat_samples(payload.samples)
        await session.commit()
    return OkResponse(ok=True)


async def claim_job(payload: ClaimJobRequest) -> ClaimJobResponse | None:
    async with SessionLocal() as session:
        result = await JobService(session, get_settings()).claim(payload)
        await session.commit()
        return result


async def complete_job(job_id: str, payload: CompleteJobRequest) -> None:
    async with SessionLocal() as session:
        await JobService(session, get_settings()).complete(job_id, payload)
        await session.commit()


async def ingest_samples(payload: list[NodeSampleUpload]) -> OkResponse:
    async with SessionLocal() as session:
        await MeteringService(session, get_settings()).ingest_samples(payload)
        await session.commit()
    return OkResponse(ok=True)
