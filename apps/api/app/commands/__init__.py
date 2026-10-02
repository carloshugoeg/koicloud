from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.enums import (
    JobStatus,
    JobType,
    UserRole,
    UserStatus,
)
from app.schemas import (
    AdminUserOut,
    ConfirmationRequiredResponse,
    JobOut,
)


def stable_uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "::".join(parts))


def now_iso() -> datetime:
    return datetime.now(tz=UTC)


def build_admin_user(
    *,
    email: str,
    full_name: str,
    role: UserRole = UserRole.CLIENT,
    status: UserStatus = UserStatus.ACTIVE,
) -> AdminUserOut:
    return AdminUserOut(
        id=stable_uuid("user", email),
        email=email,
        full_name=full_name,
        role=role,
        status=status,
        email_verified=True,
        created_at=now_iso(),
        active_subscription_plan="micro",
    )


def build_job(*, job_type: JobType, pond_id: UUID | None = None, status: JobStatus = JobStatus.QUEUED) -> JobOut:
    return JobOut(
        id=stable_uuid("job", job_type.value, str(pond_id or "none"), status.value),
        type=job_type,
        pond_id=pond_id,
        node_id=get_settings().node_id,
        status=status,
        attempts=0,
        created_at=now_iso(),
        claimed_at=None,
        completed_at=None,
        last_error=None,
    )


async def build_confirmation(
    *,
    actor: AuthContext,
    action: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> ConfirmationRequiredResponse:
    from app.commands.confirmations import propose_action

    return await propose_action(actor=actor, action=action, summary=summary, payload=payload)
