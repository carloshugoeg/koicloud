from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.base import SchemaModel
from app.core.enums import (
    ActorKind,
    BackupKind,
    BackupStatus,
    InvoiceStatus,
    JobStatus,
    JobType,
    PaymentStatus,
    PondDesiredState,
    PondObservedState,
    SQLMode,
    SubscriptionStatus,
    UserRole,
    UserStatus,
)

EXAMPLE_USER_ID = "11111111-1111-1111-1111-111111111111"
EXAMPLE_SUBSCRIPTION_ID = "22222222-2222-2222-2222-222222222222"
EXAMPLE_INVOICE_ID = "33333333-3333-3333-3333-333333333333"
EXAMPLE_INVOICE_LINE_ID = "44444444-4444-4444-4444-444444444444"
EXAMPLE_PAYMENT_ID = "55555555-5555-5555-5555-555555555555"
EXAMPLE_POND_ID = "66666666-6666-6666-6666-666666666666"
EXAMPLE_JOB_ID = "77777777-7777-7777-7777-777777777777"
EXAMPLE_BACKUP_ID = "88888888-8888-8888-8888-888888888888"
EXAMPLE_SQL_EVENT_ID = "99999999-9999-9999-9999-999999999999"
EXAMPLE_AUDIT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXAMPLE_NOW = "2026-09-22T20:00:00Z"
EXAMPLE_LATER = "2026-09-22T20:05:00Z"


def config_with_example(example: Any) -> ConfigDict:
    return ConfigDict(extra="forbid", populate_by_name=True, json_schema_extra={"example": example})


class ErrorResponse(SchemaModel):
    code: str
    message: str
    request_id: str | None = None

    model_config = config_with_example(
        {
            "code": "quota_exceeded",
            "message": "Ya alcanzaste el máximo de ponds (1) de tu plan.",
            "request_id": "req_01hf8mxv2xb8af3w0k9nvy7p9w",
        }
    )


class OkResponse(SchemaModel):
    ok: bool = True

    model_config = config_with_example({"ok": True})


class HealthResponse(SchemaModel):
    ok: bool = True
    git_sha: str

    model_config = config_with_example({"ok": True, "git_sha": "phase0-contract-freeze"})


class ReadyResponse(SchemaModel):
    ok: bool
    dependencies: dict[str, bool]

    model_config = config_with_example({"ok": True, "dependencies": {"database": True, "mcp": True}})


class UserOut(SchemaModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    nit: str | None = None
    status: UserStatus
    email_verified: bool
    created_at: datetime

    model_config = config_with_example(
        {
            "id": EXAMPLE_USER_ID,
            "email": "carlos@koicloud.dev",
            "full_name": "Carlos Hugo Escobar",
            "role": "client",
            "nit": "0614-220999-101-3",
            "status": "active",
            "email_verified": True,
            "created_at": EXAMPLE_NOW,
        }
    )


class RegisterUserRequest(SchemaModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str
    nit: str | None = None

    model_config = config_with_example(
        {
            "email": "jason@koicloud.dev",
            "password": "Sup3rSegura!2026",
            "full_name": "Jason Gutiérrez",
            "nit": "0614-100199-102-4",
        }
    )


class RegisterUserResponse(SchemaModel):
    user_id: UUID
    email_verified: bool

    model_config = config_with_example(
        {"user_id": EXAMPLE_USER_ID, "email_verified": False}
    )


class VerifyEmailRequest(SchemaModel):
    token: str

    model_config = config_with_example({"token": "verify_1u8v2m4cy1u3w8x4"})


class LoginRequest(SchemaModel):
    email: str
    password: str

    model_config = config_with_example(
        {"email": "carlos@koicloud.dev", "password": "Sup3rSegura!2026"}
    )


class RefreshTokenRequest(SchemaModel):
    refresh_token: str

    model_config = config_with_example({"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."})


class ForgotPasswordRequest(SchemaModel):
    email: str

    model_config = config_with_example({"email": "carlos@koicloud.dev"})


class ResetPasswordRequest(SchemaModel):
    token: str
    new_password: str = Field(min_length=8)

    model_config = config_with_example(
        {"token": "reset_1u8v2m4cy1u3w8x4", "new_password": "NuevaClave!2026"}
    )


class TokenPairResponse(SchemaModel):
    access_token: str
    refresh_token: str

    model_config = config_with_example(
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
        }
    )


class LoginResponse(TokenPairResponse):
    user: UserOut

    model_config = config_with_example(
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
            "user": UserOut.example_data(),
        }
    )


class UpdateProfileRequest(SchemaModel):
    full_name: str | None = None
    nit: str | None = None

    model_config = config_with_example(
        {"full_name": "Carlos H. Escobar", "nit": "0614-220999-101-3"}
    )


class PlanOut(SchemaModel):
    id: str
    name: str
    description: str
    price_monthly_usd: float
    max_ponds: int
    max_storage_gb: int
    validity_minutes: int
    postpaid: bool
    active: bool

    model_config = config_with_example(
        {
            "id": "micro",
            "name": "Micro",
            "description": "1 pond, 1 GB, backups 7 días",
            "price_monthly_usd": 5.0,
            "max_ponds": 1,
            "max_storage_gb": 1,
            "validity_minutes": 43200,
            "postpaid": False,
            "active": True,
        }
    )


class PlanListResponse(SchemaModel):
    plans: list[PlanOut]
    next_cursor: str | None = None

    model_config = config_with_example(
        {
            "plans": [
                {
                    "id": "sandbox",
                    "name": "Sandbox",
                    "description": "Pruebas internas (10 min)",
                    "price_monthly_usd": 0.0,
                    "max_ponds": 1,
                    "max_storage_gb": 1,
                    "validity_minutes": 10,
                    "postpaid": False,
                    "active": True,
                },
                PlanOut.example_data(),
                {
                    "id": "pro",
                    "name": "Pro",
                    "description": "Hasta 10 ponds, post-pago por uso",
                    "price_monthly_usd": 0.0,
                    "max_ponds": 10,
                    "max_storage_gb": 20,
                    "validity_minutes": 43200,
                    "postpaid": True,
                    "active": True,
                },
            ],
            "next_cursor": None,
        }
    )


class SubscriptionOut(SchemaModel):
    id: UUID
    user_id: UUID
    plan_id: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool

    model_config = config_with_example(
        {
            "id": EXAMPLE_SUBSCRIPTION_ID,
            "user_id": EXAMPLE_USER_ID,
            "plan_id": "micro",
            "status": "active",
            "current_period_start": EXAMPLE_NOW,
            "current_period_end": "2026-10-22T20:00:00Z",
            "cancel_at_period_end": False,
        }
    )


class MeResponse(SchemaModel):
    user: UserOut
    subscription: SubscriptionOut | None = None
    ponds_count: int

    model_config = config_with_example(
        {
            "user": UserOut.example_data(),
            "subscription": SubscriptionOut.example_data(),
            "ponds_count": 1,
        }
    )


class UserResponse(SchemaModel):
    user: UserOut

    model_config = config_with_example({"user": UserOut.example_data()})


class SubscribeRequest(SchemaModel):
    plan_id: str

    model_config = config_with_example({"plan_id": "micro"})


class SubscriptionListResponse(SchemaModel):
    subscriptions: list[SubscriptionOut]
    next_cursor: str | None = None

    model_config = config_with_example(
        {"subscriptions": [SubscriptionOut.example_data()], "next_cursor": None}
    )


class InvoiceOut(SchemaModel):
    id: UUID
    number: str
    user_id: UUID
    subscription_id: UUID
    subtotal_usd: float
    iva_usd: float
    total_usd: float
    status: InvoiceStatus
    issued_at: datetime
    pdf_path: str | None = None

    model_config = config_with_example(
        {
            "id": EXAMPLE_INVOICE_ID,
            "number": "KOI-202609-0001",
            "user_id": EXAMPLE_USER_ID,
            "subscription_id": EXAMPLE_SUBSCRIPTION_ID,
            "subtotal_usd": 5.0,
            "iva_usd": 0.65,
            "total_usd": 5.65,
            "status": "paid",
            "issued_at": EXAMPLE_NOW,
            "pdf_path": "/var/lib/koicloud/invoices/KOI-202609-0001.pdf",
        }
    )


class InvoiceLineOut(SchemaModel):
    id: UUID
    invoice_id: UUID
    description: str
    amount_usd: float

    model_config = config_with_example(
        {
            "id": EXAMPLE_INVOICE_LINE_ID,
            "invoice_id": EXAMPLE_INVOICE_ID,
            "description": "Plan Micro mensual",
            "amount_usd": 5.0,
        }
    )


class PaymentOut(SchemaModel):
    id: UUID
    invoice_id: UUID
    amount_usd: float
    status: PaymentStatus
    method: str
    processed_at: datetime | None = None

    model_config = config_with_example(
        {
            "id": EXAMPLE_PAYMENT_ID,
            "invoice_id": EXAMPLE_INVOICE_ID,
            "amount_usd": 5.65,
            "status": "succeeded",
            "method": "simulated",
            "processed_at": EXAMPLE_NOW,
        }
    )


class SubscribeResponse(SchemaModel):
    subscription: SubscriptionOut
    invoice: InvoiceOut
    payment: PaymentOut

    model_config = config_with_example(
        {
            "subscription": SubscriptionOut.example_data(),
            "invoice": InvoiceOut.example_data(),
            "payment": PaymentOut.example_data(),
        }
    )


class CancelSubscriptionResponse(SchemaModel):
    subscription: SubscriptionOut

    model_config = config_with_example({"subscription": SubscriptionOut.example_data()})


class InvoiceListResponse(SchemaModel):
    invoices: list[InvoiceOut]
    next_cursor: str | None = None

    model_config = config_with_example({"invoices": [InvoiceOut.example_data()], "next_cursor": None})


class InvoiceDetailResponse(SchemaModel):
    invoice: InvoiceOut
    lines: list[InvoiceLineOut]

    model_config = config_with_example(
        {"invoice": InvoiceOut.example_data(), "lines": [InvoiceLineOut.example_data()]}
    )


class PondOut(SchemaModel):
    id: UUID
    user_id: UUID
    plan_id: str
    node_id: str
    name: str
    engine_version: str
    desired_state: PondDesiredState
    observed_state: PondObservedState
    host_port: int
    healthy: bool
    created_at: datetime
    last_restore_at: datetime | None = None
    last_error: str | None = None

    model_config = config_with_example(
        {
            "id": EXAMPLE_POND_ID,
            "user_id": EXAMPLE_USER_ID,
            "plan_id": "micro",
            "node_id": "node-sv-01",
            "name": "inventario-demo",
            "engine_version": "16",
            "desired_state": "running",
            "observed_state": "running",
            "host_port": 15007,
            "healthy": True,
            "created_at": EXAMPLE_NOW,
            "last_restore_at": None,
            "last_error": None,
        }
    )


class PondResponse(SchemaModel):
    pond: PondOut

    model_config = config_with_example({"pond": PondOut.example_data()})


class JobOut(SchemaModel):
    id: UUID
    type: JobType
    pond_id: UUID | None = None
    node_id: str | None = None
    status: JobStatus
    attempts: int
    created_at: datetime
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    last_error: str | None = None

    model_config = config_with_example(
        {
            "id": EXAMPLE_JOB_ID,
            "type": "create_pond",
            "pond_id": EXAMPLE_POND_ID,
            "node_id": "node-sv-01",
            "status": "queued",
            "attempts": 0,
            "created_at": EXAMPLE_NOW,
            "claimed_at": None,
            "completed_at": None,
            "last_error": None,
        }
    )


class JobResponse(SchemaModel):
    job: JobOut

    model_config = config_with_example({"job": JobOut.example_data()})


class PondListResponse(SchemaModel):
    ponds: list[PondOut]
    next_cursor: str | None = None

    model_config = config_with_example({"ponds": [PondOut.example_data()], "next_cursor": None})


class CreatePondRequest(SchemaModel):
    name: str
    engine_version: str = "16"

    model_config = config_with_example({"name": "inventario-demo", "engine_version": "16"})


class CreatePondResponse(SchemaModel):
    pond: PondOut
    job: JobOut

    model_config = config_with_example(
        {
            "pond": {
                **PondOut.example_data(),
                "observed_state": "pending",
            },
            "job": JobOut.example_data(),
        }
    )


class RetryFailedJobResponse(SchemaModel):
    job: JobOut

    model_config = config_with_example({"job": JobOut.example_data()})


class DeletePondResponse(SchemaModel):
    pond: PondOut
    jobs: list[JobOut]

    model_config = config_with_example(
        {
            "pond": {
                **PondOut.example_data(),
                "desired_state": "deleted",
                "observed_state": "deleting",
            },
            "jobs": [
                {
                    **JobOut.example_data(),
                    "id": "77777777-7777-7777-7777-777777777778",
                    "type": "backup_pond",
                },
                {
                    **JobOut.example_data(),
                    "id": "77777777-7777-7777-7777-777777777779",
                    "type": "delete_pond",
                },
            ],
        }
    )


class ConnectionOut(SchemaModel):
    host: str
    port: int
    database: str
    username: str
    password: str
    uri: str

    model_config = config_with_example(
        {
            "host": "db.koicloud.dev",
            "port": 15007,
            "database": "inventario_demo",
            "username": "koi_inventario",
            "password": "p0nd-Temp!2026",
            "uri": "postgresql://koi_inventario:p0nd-Temp%212026@db.koicloud.dev:15007/inventario_demo",
        }
    )


class ConnectionResponse(SchemaModel):
    connection: ConnectionOut

    model_config = config_with_example({"connection": ConnectionOut.example_data()})


class BackupOut(SchemaModel):
    id: UUID
    pond_id: UUID
    kind: BackupKind
    status: BackupStatus
    storage_path: str
    size_bytes: int
    sha256: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = config_with_example(
        {
            "id": EXAMPLE_BACKUP_ID,
            "pond_id": EXAMPLE_POND_ID,
            "kind": "daily",
            "status": "succeeded",
            "storage_path": "/var/lib/koicloud/backups/inventario-demo/20260922.dump",
            "size_bytes": 124901,
            "sha256": "1f3e7d3ab148b8be24af9b97a10d1655db8c613de0dc02f88f752230ec7776d0",
            "created_at": EXAMPLE_NOW,
            "completed_at": EXAMPLE_NOW,
        }
    )


class BackupListResponse(SchemaModel):
    backups: list[BackupOut]
    next_cursor: str | None = None

    model_config = config_with_example(
        {"backups": [BackupOut.example_data()], "next_cursor": None}
    )


class TriggerBackupResponse(SchemaModel):
    backup: BackupOut
    job: JobOut

    model_config = config_with_example(
        {
            "backup": {
                **BackupOut.example_data(),
                "status": "queued",
                "completed_at": None,
            },
            "job": {**JobOut.example_data(), "type": "backup_pond"},
        }
    )


class RestoreBackupRequest(SchemaModel):
    backup_id: UUID

    model_config = config_with_example({"backup_id": EXAMPLE_BACKUP_ID})


class RunSQLRequest(SchemaModel):
    query: str
    mode: SQLMode = SQLMode.READ

    model_config = config_with_example({"query": "SELECT 1", "mode": "read"})


class SQLResultResponse(SchemaModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    duration_ms: int
    truncated: bool

    model_config = config_with_example(
        {
            "columns": ["?column?"],
            "rows": [[1]],
            "row_count": 1,
            "duration_ms": 4,
            "truncated": False,
        }
    )


class SQLHistoryItem(SchemaModel):
    id: UUID
    pond_id: UUID
    query_truncated: str
    mode: SQLMode
    row_count: int
    duration_ms: int
    executed_at: datetime

    model_config = config_with_example(
        {
            "id": EXAMPLE_SQL_EVENT_ID,
            "pond_id": EXAMPLE_POND_ID,
            "query_truncated": "SELECT * FROM invoices ORDER BY issued_at DESC LIMIT 10",
            "mode": "read",
            "row_count": 10,
            "duration_ms": 18,
            "executed_at": EXAMPLE_NOW,
        }
    )


class SQLHistoryResponse(SchemaModel):
    events: list[SQLHistoryItem]
    next_cursor: str | None = None

    model_config = config_with_example(
        {"events": [SQLHistoryItem.example_data()], "next_cursor": None}
    )


class UsagePondItem(SchemaModel):
    pond_id: UUID
    pond_name: str
    instance_hours: float
    storage_gb_hours: float

    model_config = config_with_example(
        {
            "pond_id": EXAMPLE_POND_ID,
            "pond_name": "inventario-demo",
            "instance_hours": 124.5,
            "storage_gb_hours": 31.2,
        }
    )


class UsageResponse(SchemaModel):
    month: str
    total_instance_hours: float
    total_storage_gb_hours: float
    ponds: list[UsagePondItem]

    model_config = config_with_example(
        {
            "month": "2026-09",
            "total_instance_hours": 124.5,
            "total_storage_gb_hours": 31.2,
            "ponds": [UsagePondItem.example_data()],
        }
    )


class AgentAccessOut(SchemaModel):
    slug: str
    url: str
    enabled: bool
    rotated_at: datetime

    model_config = config_with_example(
        {
            "slug": "demo-agent",
            "url": "https://koicloud.local/mcp",
            "enabled": True,
            "rotated_at": EXAMPLE_NOW,
        }
    )


class AgentAccessSecretOut(SchemaModel):
    slug: str
    url: str
    password: str

    model_config = config_with_example(
        {"slug": "demo-agent", "url": "https://koicloud.local/mcp", "password": "koicloud-demo"}
    )


class ToggleAgentAccessRequest(SchemaModel):
    enabled: bool

    model_config = config_with_example({"enabled": False})


class ToggleAgentAccessResponse(SchemaModel):
    enabled: bool

    model_config = config_with_example({"enabled": False})


class ConfirmationNextStep(SchemaModel):
    confirm_url: str
    cli_example: str

    model_config = config_with_example(
        {
            "confirm_url": "/api/v1/confirm/conf_create_pond_demo",
            "cli_example": "koicloud confirm conf_create_pond_demo",
        }
    )


class ConfirmationRequiredResponse(SchemaModel):
    status: Literal["confirmation_required"]
    token: str
    summary: str
    expires_at: datetime
    next: ConfirmationNextStep

    model_config = config_with_example(
        {
            "status": "confirmation_required",
            "token": "conf_create_pond_demo",
            "summary": "Se creará el pond 'inventario-demo'. Expira en 5 min.",
            "expires_at": EXAMPLE_LATER,
            "next": ConfirmationNextStep.example_data(),
        }
    )


class AdminUserOut(SchemaModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    email_verified: bool
    created_at: datetime
    active_subscription_plan: str | None = None

    model_config = config_with_example(
        {
            "id": EXAMPLE_USER_ID,
            "email": "carlos@koicloud.dev",
            "full_name": "Carlos Hugo Escobar",
            "role": "client",
            "status": "active",
            "email_verified": True,
            "created_at": EXAMPLE_NOW,
            "active_subscription_plan": "micro",
        }
    )


class AdminUserListResponse(SchemaModel):
    users: list[AdminUserOut]
    next_cursor: str | None = None

    model_config = config_with_example(
        {"users": [AdminUserOut.example_data()], "next_cursor": None}
    )


class AdminUserResponse(SchemaModel):
    user: AdminUserOut

    model_config = config_with_example({"user": AdminUserOut.example_data()})


class SuspendUserRequest(SchemaModel):
    confirm_text: str

    model_config = config_with_example({"confirm_text": "SUSPENDER"})


class AdminPondOut(SchemaModel):
    id: UUID
    owner_email: str
    name: str
    plan_id: str
    node_id: str
    desired_state: PondDesiredState
    observed_state: PondObservedState
    host_port: int
    created_at: datetime

    model_config = config_with_example(
        {
            "id": EXAMPLE_POND_ID,
            "owner_email": "carlos@koicloud.dev",
            "name": "inventario-demo",
            "plan_id": "micro",
            "node_id": "node-sv-01",
            "desired_state": "running",
            "observed_state": "running",
            "host_port": 15007,
            "created_at": EXAMPLE_NOW,
        }
    )


class AdminPondListResponse(SchemaModel):
    ponds: list[AdminPondOut]
    next_cursor: str | None = None

    model_config = config_with_example(
        {"ponds": [AdminPondOut.example_data()], "next_cursor": None}
    )


class AuditEventOut(SchemaModel):
    id: UUID
    actor_user_id: UUID | None = None
    actor_kind: ActorKind
    target_kind: str
    target_id: str
    action: str
    metadata: dict[str, Any]
    at: datetime

    model_config = config_with_example(
        {
            "id": EXAMPLE_AUDIT_ID,
            "actor_user_id": EXAMPLE_USER_ID,
            "actor_kind": "admin",
            "target_kind": "pond",
            "target_id": EXAMPLE_POND_ID,
            "action": "delete_pond",
            "metadata": {"source": "cli"},
            "at": EXAMPLE_NOW,
        }
    )


class AuditEventListResponse(SchemaModel):
    events: list[AuditEventOut]
    next_cursor: str | None = None

    model_config = config_with_example(
        {"events": [AuditEventOut.example_data()], "next_cursor": None}
    )


class HeartbeatContainer(SchemaModel):
    name: str
    state: str
    uptime: str

    model_config = config_with_example({"name": "pond-inventario-demo", "state": "running", "uptime": "2h"})


class HeartbeatSample(SchemaModel):
    pond_name: str
    size_bytes: int
    container_state: str

    model_config = config_with_example(
        {"pond_name": "inventario-demo", "size_bytes": 124901, "container_state": "running"}
    )


class HeartbeatRequest(SchemaModel):
    containers: list[HeartbeatContainer]
    samples: list[HeartbeatSample]

    model_config = config_with_example(
        {
            "containers": [HeartbeatContainer.example_data()],
            "samples": [HeartbeatSample.example_data()],
        }
    )


class ClaimJobRequest(SchemaModel):
    max_types: list[JobType] | None = None

    model_config = config_with_example({"max_types": ["create_pond", "backup_pond"]})


class ClaimedJobPayload(SchemaModel):
    name: str
    host_port: int
    memory_mb: int
    cpus: float
    db_password_plain: str
    image: str
    backup_id: str | None = None

    model_config = config_with_example(
        {
            "name": "inventario-demo",
            "host_port": 15007,
            "memory_mb": 512,
            "cpus": 0.5,
            "db_password_plain": "p0nd-Temp!2026",
            "image": "postgres:16-alpine",
        }
    )


class ClaimedJob(SchemaModel):
    id: UUID
    type: JobType
    pond_id: UUID | None = None
    payload: ClaimedJobPayload

    model_config = config_with_example(
        {
            "id": EXAMPLE_JOB_ID,
            "type": "create_pond",
            "pond_id": EXAMPLE_POND_ID,
            "payload": ClaimedJobPayload.example_data(),
        }
    )


class ClaimJobResponse(SchemaModel):
    job: ClaimedJob

    model_config = config_with_example({"job": ClaimedJob.example_data()})


class CompleteJobRequest(SchemaModel):
    status: Literal["succeeded", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = None

    model_config = config_with_example(
        {"status": "succeeded", "result": {"observed_state": "running"}, "error": None}
    )


class NodeSampleUpload(SchemaModel):
    pond_id: UUID
    size_bytes: int
    container_state: str

    model_config = config_with_example(
        {"pond_id": EXAMPLE_POND_ID, "size_bytes": 124901, "container_state": "running"}
    )


class MCPInfoResponse(SchemaModel):
    enabled: bool
    endpoint: str
    read_only_tools: list[str]
    mutable_tools: list[str]
    prompt_summary: str

    model_config = config_with_example(
        {
            "enabled": True,
            "endpoint": "/mcp",
            "read_only_tools": [
                "whoami",
                "list_ponds",
                "get_pond",
                "get_connection",
                "list_subscriptions",
                "list_backups",
                "get_usage",
            ],
            "mutable_tools": [
                "create_pond",
                "delete_pond",
                "restore_backup",
                "run_sql",
                "confirm_action",
                "cancel_confirmation",
            ],
            "prompt_summary": "Las tools mutantes requieren explicación previa y confirmación explícita.",
        }
    )


class JsonRpcRequest(SchemaModel):
    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None

    model_config = config_with_example(
        {
            "jsonrpc": "2.0",
            "id": "tool-1",
            "method": "tools/call",
            "params": {"name": "list_ponds", "arguments": {}},
        }
    )


class JsonRpcResponse(SchemaModel):
    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    result: dict[str, Any] | list[Any] | str | None = None
    error: dict[str, Any] | None = None

    model_config = config_with_example(
        {
            "jsonrpc": "2.0",
            "id": "tool-1",
            "result": {"status": "ok", "message": "MCP skeleton ready"},
            "error": None,
        }
    )
