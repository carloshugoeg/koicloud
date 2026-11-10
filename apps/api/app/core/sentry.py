from __future__ import annotations

import os

import sentry_sdk


def init_sentry() -> None:
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return
    if sentry_sdk.is_initialized():
        return
    sentry_sdk.init(
        dsn=dsn,
        default_integrations=False,
        integrations=[],
        send_default_pii=False,
    )


def capture_job_failure(*, code: str, job_id: object, pond_id: object | None = None) -> None:
    # Local import so tests can swap sys.modules["sentry_sdk"] without reloading.
    import sentry_sdk as sdk

    if not sdk.is_initialized():
        return
    parts = [code, f"job={job_id}"]
    if pond_id is not None:
        parts.append(f"pond={pond_id}")
    message = " ".join(parts)
    sdk.capture_message(message[:500], level="error")
