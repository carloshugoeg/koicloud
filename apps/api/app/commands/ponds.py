from __future__ import annotations

from uuid import UUID

from app.commands import build_confirmation, build_job, build_pond
from app.core.auth import AuthContext
from app.core.enums import AppSurface, JobType, PondDesiredState, PondObservedState
from app.schemas import (
    ConfirmationRequiredResponse,
    ConnectionOut,
    ConnectionResponse,
    CreatePondRequest,
    CreatePondResponse,
    DeletePondResponse,
    JobOut,
    PondListResponse,
    PondResponse,
    RetryFailedJobResponse,
)


def _requires_confirmation(surface: AppSurface, confirm_token: str | None) -> bool:
    return surface in {AppSurface.CLI, AppSurface.MCP} and not confirm_token


def _connection_for_pond(pond_name: str, host_port: int) -> ConnectionOut:
    database = pond_name.replace("-", "_")
    username = f"koi_{database}"[:24]
    password = "p0nd-Temp!2026"
    return ConnectionOut(
        host="db.koicloud.dev",
        port=host_port,
        database=database,
        username=username,
        password=password,
        uri=f"postgresql://{username}:{password}@db.koicloud.dev:{host_port}/{database}",
    )


async def list_ponds(actor: AuthContext) -> PondListResponse:
    ponds = [
        build_pond(name="inventario-demo", user_id=actor.user_id),
        build_pond(name="reportes-demo", user_id=actor.user_id, observed_state=PondObservedState.PROVISIONING),
    ]
    return PondListResponse(ponds=ponds, next_cursor=None)


async def create_pond(
    payload: CreatePondRequest,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> CreatePondResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return build_confirmation(
            action="create_pond",
            summary=f"Se creará el pond '{payload.name}'. Expira en 5 min.",
        )

    pond = build_pond(name=payload.name, user_id=actor.user_id, observed_state=PondObservedState.PENDING)
    pond.engine_version = payload.engine_version
    job = build_job(job_type=JobType.CREATE_POND, pond_id=pond.id)
    return CreatePondResponse(pond=pond, job=job)


async def get_pond(actor: AuthContext, pond_id: UUID) -> PondResponse:
    pond = build_pond(name="inventario-demo", user_id=actor.user_id)
    pond.id = pond_id
    return PondResponse(pond=pond)


async def get_pond_by_name(actor: AuthContext, name: str) -> PondResponse:
    return PondResponse(pond=build_pond(name=name, user_id=actor.user_id))


async def get_connection(actor: AuthContext, pond_id: UUID) -> ConnectionResponse:
    pond = build_pond(name="inventario-demo", user_id=actor.user_id)
    pond.id = pond_id
    return ConnectionResponse(connection=_connection_for_pond(pond.name, pond.host_port))


async def retry_failed_job(
    pond_id: UUID,
    *,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> RetryFailedJobResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return build_confirmation(
            action="retry_failed_job",
            summary=f"Se reintentará el último job fallido del pond '{pond_id}'. Expira en 5 min.",
        )
    job = build_job(job_type=JobType.CREATE_POND, pond_id=pond_id)
    return RetryFailedJobResponse(job=job)


async def delete_pond(
    actor: AuthContext,
    pond_id: UUID,
    *,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> DeletePondResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return build_confirmation(
            action="delete_pond",
            summary=(
                "Se eliminará el pond solicitado. "
                "Se creará un respaldo previo automático. Expira en 5 min."
            ),
        )

    pond = build_pond(name="inventario-demo", user_id=actor.user_id)
    pond.id = pond_id
    pond.desired_state = PondDesiredState.DELETED
    pond.observed_state = PondObservedState.DELETING
    jobs: list[JobOut] = [
        build_job(job_type=JobType.BACKUP_POND, pond_id=pond_id),
        build_job(job_type=JobType.DELETE_POND, pond_id=pond_id),
    ]
    return DeletePondResponse(pond=pond, jobs=jobs)
