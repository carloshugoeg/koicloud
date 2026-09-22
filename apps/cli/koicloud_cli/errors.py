from __future__ import annotations

from typing import Any

LOGGED_OUT_MESSAGE = "Primero corré `koicloud login`."


class KoiCloudCliError(Exception):
    """Base error for CLI failures."""


class NotLoggedInError(KoiCloudCliError):
    """Raised when a command requires saved tokens."""

    def __init__(self, message: str = LOGGED_OUT_MESSAGE) -> None:
        super().__init__(message)


class ApiError(KoiCloudCliError):
    """HTTP error returned by the control plane."""

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        code: str | None = None,
        request_id: str | None = None,
        payload: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.request_id = request_id
        self.payload = payload


class ConfirmationRequiredError(ApiError):
    """Specialized error raised for the propose -> confirm contract."""

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        token: str,
        summary: str,
        expires_at: str | None = None,
        next_action: dict[str, Any] | None = None,
        code: str | None = "confirmation_required",
        request_id: str | None = None,
        payload: Any | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            message=message,
            code=code,
            request_id=request_id,
            payload=payload,
        )
        self.token = token
        self.summary = summary
        self.expires_at = expires_at
        self.next_action = next_action or {}


def build_api_error(status_code: int, payload: Any) -> ApiError:
    """Turn an API response body into a typed CLI error."""

    if isinstance(payload, dict):
        code = payload.get("code") or payload.get("status")
        message = payload.get("message") or payload.get("summary") or f"HTTP {status_code}"
        request_id = payload.get("request_id")
        if code == "confirmation_required" and payload.get("token") and payload.get("summary"):
            return ConfirmationRequiredError(
                status_code=status_code,
                message=message,
                code=code,
                request_id=request_id,
                payload=payload,
                token=payload["token"],
                summary=payload["summary"],
                expires_at=payload.get("expires_at"),
                next_action=payload.get("next"),
            )
        return ApiError(
            status_code=status_code,
            code=code,
            message=message,
            request_id=request_id,
            payload=payload,
        )

    return ApiError(status_code=status_code, message=str(payload), payload=payload)


def render_api_error(error: ApiError) -> str:
    """Format a user-facing error message."""

    if isinstance(error, ConfirmationRequiredError):
        cli_example = None
        if isinstance(error.next_action, dict):
            cli_example = error.next_action.get("cli_example")
        parts = [error.summary, f"Token: {error.token}"]
        if cli_example:
            parts.append(f"Confirmá con: {cli_example}")
        return "\n".join(parts)

    if error.code:
        return f"{error.message} [{error.code}]"
    return error.message
