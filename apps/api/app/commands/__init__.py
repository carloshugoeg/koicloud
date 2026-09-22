from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.config import get_settings
from app.core.enums import (
    JobStatus,
    JobType,
    PondDesiredState,
    PondObservedState,
    UserRole,
    UserStatus,
)
from app.core.security import generate_confirmation_token
from app.schemas import (
    AdminUserOut,
    ConfirmationNextStep,
    ConfirmationRequiredResponse,
    JobOut,
    PondOut,
    UserOut,
)


def stable_uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "::".join(parts))


def now_iso() -> datetime:
    return datetime.now(tz=UTC)


def build_user(
    *,
    email: str,
    full_name: str,
    role: UserRole = UserRole.CLIENT,
    nit: str | None = "0614-220999-101-3",
) -> UserOut:
    return UserOut(
        id=stable_uuid("user", email),
        email=email,
        full_name=full_name,
        role=role,
        nit=nit,
        status=UserStatus.ACTIVE,
        email_verified=True,
        created_at=now_iso(),
    )


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


def build_pond(*, name: str, user_id: str, observed_state: PondObservedState = PondObservedState.RUNNING) -> PondOut:
    stable_id = stable_uuid("pond", user_id, name)
    return PondOut(
        id=stable_id,
        user_id=UUID(user_id),
        plan_id="micro",
        node_id=get_settings().node_id,
        name=name,
        engine_version="16",
        desired_state=PondDesiredState.RUNNING,
        observed_state=observed_state,
        host_port=15000 + (stable_id.int % 500),
        healthy=observed_state == PondObservedState.RUNNING,
        created_at=now_iso(),
        last_restore_at=None,
        last_error=None,
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


def build_confirmation(*, action: str, summary: str) -> ConfirmationRequiredResponse:
    settings = get_settings()
    token = generate_confirmation_token(action)
    return ConfirmationRequiredResponse(
        status="confirmation_required",
        token=token,
        summary=summary,
        expires_at=(now_iso() + timedelta(seconds=settings.confirm_ttl_seconds)).replace(microsecond=0),
        next=ConfirmationNextStep(
            confirm_url=f"/api/v1/confirm/{token}",
            cli_example=f"koicloud confirm {token}",
        ),
    )
