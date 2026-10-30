from __future__ import annotations

from uuid import UUID

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface
from app.modules.ponds.service import PondService
from app.schemas import (
    ConfirmationRequiredResponse,
    ConnectionResponse,
    CreatePondRequest,
    CreatePondResponse,
    DeletePondResponse,
    PondListResponse,
    PondResponse,
    RetryFailedJobResponse,
    StartPondResponse,
    StopPondResponse,
)


def _requires_confirmation(surface: AppSurface, confirm_token: str | None) -> bool:
    return surface in {AppSurface.CLI, AppSurface.MCP} and not confirm_token


async def list_ponds(actor: AuthContext) -> PondListResponse:
    async with SessionLocal() as session:
        ponds = await PondService(session, get_settings()).list_for_user(actor)
        return PondListResponse(ponds=ponds, next_cursor=None)


async def create_pond(
    payload: CreatePondRequest,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> CreatePondResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return await build_confirmation(
            actor=actor,
            action="create_pond",
            summary=f"Se creará el pond '{payload.name}'. Expira en 5 min.",
            payload=payload.model_dump(mode="json"),
        )

    async with SessionLocal() as session:
        pond, job = await PondService(session, get_settings()).create(
            actor,
            name=payload.name,
            engine_version=payload.engine_version,
        )
        await session.commit()
        return CreatePondResponse(pond=pond, job=job)


async def get_pond(actor: AuthContext, pond_id: UUID) -> PondResponse:
    async with SessionLocal() as session:
        pond = await PondService(session, get_settings()).get_owned_out(actor, pond_id)
        return PondResponse(pond=pond)


async def get_pond_by_name(actor: AuthContext, name: str) -> PondResponse:
    async with SessionLocal() as session:
        pond = await PondService(session, get_settings()).get_owned_by_name_out(actor, name)
        return PondResponse(pond=pond)


async def get_connection(actor: AuthContext, pond_id: UUID) -> ConnectionResponse:
    async with SessionLocal() as session:
        connection = await PondService(session, get_settings()).connection_for_owned(actor, pond_id)
        return ConnectionResponse(connection=connection)


async def retry_failed_job(
    pond_id: UUID,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> RetryFailedJobResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return await build_confirmation(
            actor=actor,
            action="retry_failed_job",
            summary=f"Se reintentará el último job fallido del pond '{pond_id}'. Expira en 5 min.",
            payload={"pond_id": str(pond_id)},
        )
    async with SessionLocal() as session:
        job = await PondService(session, get_settings()).retry_failed(actor, pond_id)
        await session.commit()
        return RetryFailedJobResponse(job=job)


async def delete_pond(
    actor: AuthContext,
    pond_id: UUID,
    *,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> DeletePondResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        async with SessionLocal() as session:
            pond, pond_status = await PondService(session, get_settings()).get_owned(
                actor, pond_id
            )
            pond_name = pond.name
            observed = (
                pond_status.observed_state.value
                if hasattr(pond_status.observed_state, "value")
                else str(pond_status.observed_state)
            )
        return await build_confirmation(
            actor=actor,
            action="delete_pond",
            summary=(
                f"Se eliminará el pond '{pond_name}' (estado: {observed}). "
                "Se encolará un respaldo pre_delete y luego el borrado. Expira en 5 min."
            ),
            payload={"pond_id": str(pond_id)},
        )

    async with SessionLocal() as session:
        pond, jobs = await PondService(session, get_settings()).delete(actor, pond_id)
        await session.commit()
        return DeletePondResponse(pond=pond, jobs=jobs)


async def stop_pond(
    actor: AuthContext,
    pond_id: UUID,
    *,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> StopPondResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        async with SessionLocal() as session:
            pond, _status = await PondService(session, get_settings()).get_owned(actor, pond_id)
            pond_name = pond.name
        return await build_confirmation(
            actor=actor,
            action="stop_pond",
            summary=f"Se detendrá el pond '{pond_name}'. Expira en 5 min.",
            payload={"pond_id": str(pond_id)},
        )

    async with SessionLocal() as session:
        pond, job = await PondService(session, get_settings()).stop(actor, pond_id)
        await session.commit()
        return StopPondResponse(pond=pond, job=job)


async def start_pond(
    actor: AuthContext,
    pond_id: UUID,
    *,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> StartPondResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        async with SessionLocal() as session:
            pond, _status = await PondService(session, get_settings()).get_owned(actor, pond_id)
            pond_name = pond.name
        return await build_confirmation(
            actor=actor,
            action="start_pond",
            summary=f"Se iniciará el pond '{pond_name}'. Expira en 5 min.",
            payload={"pond_id": str(pond_id)},
        )

    async with SessionLocal() as session:
        pond, job = await PondService(session, get_settings()).start(actor, pond_id)
        await session.commit()
        return StartPondResponse(pond=pond, job=job)
