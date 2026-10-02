from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.commands import admin as admin_commands
from app.commands import agent_access as agent_access_commands
from app.commands import auth as auth_commands
from app.commands import backups as backup_commands
from app.commands import billing as billing_commands
from app.commands import confirmations as confirmation_commands
from app.commands import ponds as pond_commands
from app.commands import sql as sql_commands
from app.commands import usage as usage_commands
from app.commands import users as user_commands
from app.core.auth import AuthContext, get_admin_user, get_current_user
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.deps import get_confirmation_token, get_surface
from app.core.enums import AppSurface
from app.modules.auth import AuthService
from app.modules.auth.service import REFRESH_COOKIE
from app.schemas import (
    AdminPondListResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AgentAccessOut,
    AgentAccessSecretOut,
    AuditEventListResponse,
    BackupListResponse,
    CancelSubscriptionResponse,
    ConfirmationRequiredResponse,
    ConnectionResponse,
    CreatePondRequest,
    CreatePondResponse,
    DeletePondResponse,
    ErrorResponse,
    ForgotPasswordRequest,
    HealthResponse,
    InvoiceDetailResponse,
    InvoiceListResponse,
    JobResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    OkResponse,
    PlanListResponse,
    PondListResponse,
    PondResponse,
    ReadyResponse,
    RefreshTokenRequest,
    RegisterUserRequest,
    RegisterUserResponse,
    ResetPasswordRequest,
    RestoreBackupRequest,
    RetryFailedJobResponse,
    RunSQLRequest,
    SQLHistoryResponse,
    SQLResultResponse,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionListResponse,
    SuspendUserRequest,
    ToggleAgentAccessRequest,
    ToggleAgentAccessResponse,
    TokenPairResponse,
    TriggerBackupResponse,
    UpdateProfileRequest,
    UsageResponse,
    UserResponse,
    VerifyEmailRequest,
)

router = APIRouter()


def _error_responses(*codes: int, confirmation: bool = False) -> dict[int, dict[str, Any]]:
    responses = {code: {"model": ErrorResponse} for code in codes}
    if confirmation:
        responses[409] = {"model": ConfirmationRequiredResponse}
    return responses


def _render(payload: Any, *, success_status: int) -> Response:
    if isinstance(payload, ConfirmationRequiredResponse):
        return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))
    if payload is None:
        return Response(status_code=success_status)
    if isinstance(payload, BaseModel):
        return JSONResponse(status_code=success_status, content=payload.model_dump(mode="json"))
    if isinstance(payload, bytes):
        return Response(content=payload, media_type="application/pdf", status_code=success_status)
    return JSONResponse(status_code=success_status, content=payload)


@router.post(
    "/auth/register",
    response_model=RegisterUserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="register_user",
    tags=["auth"],
    responses=_error_responses(409, 422),
)
async def register_user(payload: RegisterUserRequest) -> RegisterUserResponse:
    return await AuthService.register_user(payload)


@router.post(
    "/auth/verify",
    response_model=RegisterUserResponse,
    operation_id="verify_email",
    tags=["auth"],
    responses=_error_responses(401, 404, 410),
)
async def verify_email(payload: VerifyEmailRequest) -> RegisterUserResponse:
    return await AuthService.verify_email(payload)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.refresh_ttl_days * 24 * 60 * 60,
        path=settings.api_prefix,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=REFRESH_COOKIE, path=settings.api_prefix)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    operation_id="issue_tokens",
    tags=["auth"],
    responses=_error_responses(401, 403, 429),
)
async def issue_tokens(payload: LoginRequest, response: Response) -> LoginResponse:
    result = await AuthService.issue_tokens(payload)
    _set_refresh_cookie(response, result.refresh_token)
    return result


@router.post(
    "/auth/refresh",
    response_model=TokenPairResponse,
    operation_id="rotate_refresh",
    tags=["auth"],
    responses=_error_responses(401),
)
async def rotate_refresh(payload: RefreshTokenRequest, response: Response) -> TokenPairResponse:
    result = await AuthService.rotate_refresh(payload)
    _set_refresh_cookie(response, result.refresh_token)
    return result


@router.post(
    "/auth/forgot",
    response_model=OkResponse,
    operation_id="send_reset_token",
    tags=["auth"],
    responses=_error_responses(429),
)
async def send_reset_token(payload: ForgotPasswordRequest) -> OkResponse:
    return await auth_commands.send_reset_token(payload)


@router.post(
    "/auth/reset",
    response_model=OkResponse,
    operation_id="reset_password",
    tags=["auth"],
    responses=_error_responses(401, 422),
)
async def reset_password(payload: ResetPasswordRequest) -> OkResponse:
    return await auth_commands.reset_password(payload)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="revoke_refresh",
    tags=["auth"],
    responses=_error_responses(401),
)
async def revoke_refresh(
    request: Request,
    response: Response,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> Response:
    await AuthService.logout(
        refresh_token=request.cookies.get(REFRESH_COOKIE),
        user_id=UUID(actor.user_id),
    )
    _clear_refresh_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=MeResponse,
    operation_id="get_me",
    tags=["users"],
    responses=_error_responses(401),
)
async def get_me(actor: Annotated[AuthContext, Depends(get_current_user)]) -> MeResponse:
    return await user_commands.get_me(actor)


@router.patch(
    "/me",
    response_model=UserResponse,
    operation_id="update_profile",
    tags=["users"],
    responses=_error_responses(401),
)
async def update_profile(
    payload: UpdateProfileRequest,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> UserResponse:
    return await user_commands.update_profile(actor, payload)


@router.get(
    "/plans",
    response_model=PlanListResponse,
    operation_id="list_plans",
    tags=["billing"],
)
async def list_plans() -> PlanListResponse:
    return await billing_commands.list_plans()


@router.get(
    "/subscriptions",
    response_model=SubscriptionListResponse,
    operation_id="list_my_subscriptions",
    tags=["billing"],
    responses=_error_responses(401),
)
async def list_subscriptions(
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> SubscriptionListResponse:
    return await billing_commands.list_my_subscriptions(actor)


@router.post(
    "/subscriptions",
    response_model=SubscribeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="subscribe",
    tags=["billing"],
    responses=_error_responses(401, 409, confirmation=True),
)
async def subscribe(
    payload: SubscribeRequest,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await billing_commands.subscribe(
        payload,
        actor=actor,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_202_ACCEPTED)


@router.post(
    "/subscriptions/{subscription_id}/cancel",
    response_model=CancelSubscriptionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="cancel_subscription",
    tags=["billing"],
    responses=_error_responses(401, 404, 409, confirmation=True),
)
async def cancel_subscription(
    subscription_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await billing_commands.cancel_subscription(
        subscription_id,
        actor=actor,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_202_ACCEPTED)


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    operation_id="list_invoices",
    tags=["billing"],
    responses=_error_responses(401),
)
async def list_invoices(
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> InvoiceListResponse:
    return await billing_commands.list_invoices(actor)


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceDetailResponse,
    operation_id="get_invoice",
    tags=["billing"],
    responses=_error_responses(401, 404),
)
async def get_invoice(
    invoice_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> InvoiceDetailResponse:
    return await billing_commands.get_invoice(actor, invoice_id)


@router.get(
    "/invoices/{invoice_id}/pdf",
    operation_id="get_invoice_pdf",
    tags=["billing"],
    responses={200: {"content": {"application/pdf": {}}}, **_error_responses(401, 404)},
)
async def get_invoice_pdf(
    invoice_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> Response:
    return _render(await billing_commands.get_invoice_pdf(actor, invoice_id), success_status=200)


@router.get(
    "/ponds",
    response_model=PondListResponse,
    operation_id="list_ponds",
    tags=["ponds"],
    responses=_error_responses(401),
)
async def list_ponds(actor: Annotated[AuthContext, Depends(get_current_user)]) -> PondListResponse:
    return await pond_commands.list_ponds(actor)


@router.post(
    "/ponds",
    response_model=CreatePondResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="create_pond",
    tags=["ponds"],
    responses=_error_responses(401, 409, 503, confirmation=True),
)
async def create_pond(
    payload: CreatePondRequest,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await pond_commands.create_pond(
        payload,
        actor=actor,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_202_ACCEPTED)


@router.get(
    "/ponds/{pond_id}",
    response_model=PondResponse,
    operation_id="get_pond",
    tags=["ponds"],
    responses=_error_responses(401, 403, 404),
)
async def get_pond(
    pond_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> PondResponse:
    return await pond_commands.get_pond(actor, pond_id)


@router.get(
    "/ponds/by-name/{name}",
    response_model=PondResponse,
    operation_id="get_pond_by_name",
    tags=["ponds"],
    responses=_error_responses(401, 403, 404),
)
async def get_pond_by_name(
    name: str,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> PondResponse:
    return await pond_commands.get_pond_by_name(actor, name)


@router.get(
    "/ponds/{pond_id}/connection",
    response_model=ConnectionResponse,
    operation_id="get_connection",
    tags=["ponds"],
    responses=_error_responses(401, 403, 404),
)
async def get_connection(
    pond_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> ConnectionResponse:
    return await pond_commands.get_connection(actor, pond_id)


@router.post(
    "/ponds/{pond_id}/retry",
    response_model=RetryFailedJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="retry_failed_job",
    tags=["ponds"],
    responses=_error_responses(401, 404, 409, confirmation=True),
)
async def retry_failed_job(
    pond_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await pond_commands.retry_failed_job(
        pond_id,
        actor=actor,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_202_ACCEPTED)


@router.delete(
    "/ponds/{pond_id}",
    response_model=DeletePondResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="delete_pond",
    tags=["ponds"],
    responses=_error_responses(401, 403, 404, 409, confirmation=True),
)
async def delete_pond(
    pond_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await pond_commands.delete_pond(
        actor,
        pond_id,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_202_ACCEPTED)


@router.get(
    "/ponds/{pond_id}/backups",
    response_model=BackupListResponse,
    operation_id="list_backups",
    tags=["backups"],
    responses=_error_responses(401, 403, 404),
)
async def list_backups(
    pond_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> BackupListResponse:
    return await backup_commands.list_backups(actor, pond_id)


@router.post(
    "/ponds/{pond_id}/backups",
    response_model=TriggerBackupResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="trigger_backup",
    tags=["backups"],
    responses=_error_responses(401, 403, 404, 409, confirmation=True),
)
async def trigger_backup(
    pond_id: UUID,
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await backup_commands.trigger_backup(
        pond_id,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_202_ACCEPTED)


@router.post(
    "/ponds/{pond_id}/restore",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="restore_backup",
    tags=["backups"],
    responses=_error_responses(401, 403, 404, 409, confirmation=True),
)
async def restore_backup(
    pond_id: UUID,
    payload: RestoreBackupRequest,
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await backup_commands.restore_backup(
        pond_id,
        payload,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_202_ACCEPTED)


@router.post(
    "/ponds/{pond_id}/sql",
    response_model=SQLResultResponse,
    operation_id="run_sql",
    tags=["sql"],
    responses=_error_responses(400, 401, 403, 404, 409, 504, confirmation=True),
)
async def run_sql(
    pond_id: UUID,
    payload: RunSQLRequest,
    actor: Annotated[AuthContext, Depends(get_current_user)],
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await sql_commands.run_sql(
        pond_id,
        payload,
        actor=actor,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_200_OK)


@router.get(
    "/ponds/{pond_id}/sql/history",
    response_model=SQLHistoryResponse,
    operation_id="list_sql_history",
    tags=["sql"],
    responses=_error_responses(401, 403, 404),
)
async def list_sql_history(
    pond_id: UUID,
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> SQLHistoryResponse:
    return await sql_commands.list_sql_history(actor, pond_id)


@router.get(
    "/usage",
    response_model=UsageResponse,
    operation_id="get_usage",
    tags=["usage"],
    responses=_error_responses(401),
)
async def get_usage(
    actor: Annotated[AuthContext, Depends(get_current_user)],
    month: str | None = Query(default=None, description="Mes en formato YYYY-MM"),
) -> UsageResponse:
    return await usage_commands.get_usage(actor, month)


@router.get(
    "/agent-access",
    response_model=AgentAccessOut,
    operation_id="get_agent_access",
    tags=["agent-access"],
    responses=_error_responses(401),
)
async def get_agent_access(
    actor: Annotated[AuthContext, Depends(get_current_user)],
) -> AgentAccessOut:
    return await agent_access_commands.get_agent_access(actor)


@router.post(
    "/agent-access/rotate",
    response_model=AgentAccessSecretOut,
    operation_id="rotate_agent_password",
    tags=["agent-access"],
    responses=_error_responses(401, 409, confirmation=True),
)
async def rotate_agent_password(
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await agent_access_commands.rotate_agent_password(
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_200_OK)


@router.post(
    "/agent-access/toggle",
    response_model=ToggleAgentAccessResponse,
    operation_id="toggle_agent_access",
    tags=["agent-access"],
    responses=_error_responses(401, 409, confirmation=True),
)
async def toggle_agent_access(
    payload: ToggleAgentAccessRequest,
    surface: Annotated[AppSurface, Depends(get_surface)],
    confirm_token: Annotated[str | None, Depends(get_confirmation_token)],
) -> Response:
    result = await agent_access_commands.toggle_agent_access(
        payload,
        surface=surface,
        confirm_token=confirm_token,
    )
    return _render(result, success_status=status.HTTP_200_OK)


@router.post(
    "/confirm/{token}",
    operation_id="confirm_action",
    tags=["confirmations"],
    responses=_error_responses(401, 404, 409, 410),
)
async def confirm_action(
    token: str,
    _: Annotated[AuthContext, Depends(get_current_user)],
) -> dict[str, Any]:
    return await confirmation_commands.confirm_action(token)


@router.delete(
    "/confirm/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="discard_pending_confirmation",
    tags=["confirmations"],
    responses=_error_responses(401, 404, 410),
)
async def discard_pending_confirmation(
    token: str,
    _: Annotated[AuthContext, Depends(get_current_user)],
) -> Response:
    await confirmation_commands.discard_pending_confirmation(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/admin/users",
    response_model=AdminUserListResponse,
    operation_id="admin_list_users",
    tags=["admin"],
    responses=_error_responses(401, 403),
)
async def admin_list_users(
    _: Annotated[AuthContext, Depends(get_admin_user)],
) -> AdminUserListResponse:
    return await admin_commands.admin_list_users()


@router.post(
    "/admin/users/{user_id}/suspend",
    response_model=AdminUserResponse,
    operation_id="suspend_user",
    tags=["admin"],
    responses=_error_responses(401, 403, 404, 409),
)
async def suspend_user(
    user_id: UUID,
    payload: SuspendUserRequest,
    _: Annotated[AuthContext, Depends(get_admin_user)],
) -> AdminUserResponse:
    return await admin_commands.suspend_user(user_id, payload)


@router.post(
    "/admin/users/{user_id}/reactivate",
    response_model=AdminUserResponse,
    operation_id="reactivate_user",
    tags=["admin"],
    responses=_error_responses(401, 403, 404),
)
async def reactivate_user(
    user_id: UUID,
    _: Annotated[AuthContext, Depends(get_admin_user)],
) -> AdminUserResponse:
    return await admin_commands.reactivate_user(user_id)


@router.get(
    "/admin/ponds",
    response_model=AdminPondListResponse,
    operation_id="admin_list_ponds",
    tags=["admin"],
    responses=_error_responses(401, 403),
)
async def admin_list_ponds(
    _: Annotated[AuthContext, Depends(get_admin_user)],
) -> AdminPondListResponse:
    return await admin_commands.admin_list_ponds()


@router.get(
    "/admin/audit",
    response_model=AuditEventListResponse,
    operation_id="admin_list_audit",
    tags=["admin"],
    responses=_error_responses(401, 403),
)
async def admin_list_audit(
    _: Annotated[AuthContext, Depends(get_admin_user)],
) -> AuditEventListResponse:
    return await admin_commands.admin_list_audit()


@router.get("/health", response_model=HealthResponse, operation_id="health", tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(ok=True, git_sha=get_settings().app_version)


@router.get("/ready", response_model=ReadyResponse, operation_id="ready", tags=["health"])
async def ready() -> ReadyResponse:
    database_ok = False
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
            database_ok = True
    except Exception:
        database_ok = False
    return ReadyResponse(ok=database_ok, dependencies={"database": database_ok, "mcp": True})
