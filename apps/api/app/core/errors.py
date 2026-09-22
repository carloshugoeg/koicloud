from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    EMAIL_NOT_VERIFIED = "email_not_verified"
    ACCOUNT_SUSPENDED = "account_suspended"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    EMAIL_TAKEN = "email_taken"
    PASSWORD_TOO_WEAK = "password_too_weak"
    PLAN_REQUIRED = "plan_required"
    QUOTA_EXCEEDED = "quota_exceeded"
    POND_NAME_TAKEN = "pond_name_taken"
    POND_NOT_FOUND = "pond_not_found"
    POND_BUSY = "pond_busy"
    NODE_UNAVAILABLE = "node_unavailable"
    SQL_READONLY_VIOLATION = "sql_readonly_violation"
    SQL_TIMEOUT = "sql_timeout"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_NOT_FOUND = "confirmation_not_found"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    CONFIRMATION_ACTION_MISMATCH = "confirmation_action_mismatch"
    AGENT_DISABLED = "agent_disabled"
    AGENT_BAD_CREDENTIALS = "agent_bad_credentials"
    NOT_OWNER = "not_owner"
    ADMIN_ONLY = "admin_only"
    RATE_LIMITED = "rate_limited"
    DISK_FULL = "disk_full"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    http_status: int
    message: str


ERROR_CATALOG: dict[ErrorCode, ErrorSpec] = {
    ErrorCode.INVALID_CREDENTIALS: ErrorSpec(401, "Correo o contraseña incorrectos"),
    ErrorCode.EMAIL_NOT_VERIFIED: ErrorSpec(403, "Verificá tu correo antes de continuar"),
    ErrorCode.ACCOUNT_SUSPENDED: ErrorSpec(403, "Cuenta suspendida por el administrador"),
    ErrorCode.TOKEN_EXPIRED: ErrorSpec(401, "Sesión expirada, iniciá sesión otra vez"),
    ErrorCode.TOKEN_INVALID: ErrorSpec(401, "Token inválido o mal formado"),
    ErrorCode.EMAIL_TAKEN: ErrorSpec(409, "Ese correo ya está registrado"),
    ErrorCode.PASSWORD_TOO_WEAK: ErrorSpec(422, "La contraseña no cumple el mínimo de seguridad"),
    ErrorCode.PLAN_REQUIRED: ErrorSpec(409, "Necesitás una suscripción activa"),
    ErrorCode.QUOTA_EXCEEDED: ErrorSpec(409, "Ya alcanzaste el máximo de ponds de tu plan"),
    ErrorCode.POND_NAME_TAKEN: ErrorSpec(409, "Ya existe un pond con ese nombre"),
    ErrorCode.POND_NOT_FOUND: ErrorSpec(404, "No existe el pond solicitado"),
    ErrorCode.POND_BUSY: ErrorSpec(409, "El pond ya tiene un job activo"),
    ErrorCode.NODE_UNAVAILABLE: ErrorSpec(503, "No hay nodos disponibles en este momento"),
    ErrorCode.SQL_READONLY_VIOLATION: ErrorSpec(
        400, "La query es de escritura pero el modo es read"
    ),
    ErrorCode.SQL_TIMEOUT: ErrorSpec(504, "La consulta excedió el límite de 10 segundos"),
    ErrorCode.CONFIRMATION_REQUIRED: ErrorSpec(409, "La acción requiere confirmación explícita"),
    ErrorCode.CONFIRMATION_NOT_FOUND: ErrorSpec(404, "El token de confirmación no existe"),
    ErrorCode.CONFIRMATION_EXPIRED: ErrorSpec(410, "El token de confirmación ya expiró"),
    ErrorCode.CONFIRMATION_ACTION_MISMATCH: ErrorSpec(
        409, "El token no corresponde a esta acción"
    ),
    ErrorCode.AGENT_DISABLED: ErrorSpec(403, "El acceso agente está desactivado"),
    ErrorCode.AGENT_BAD_CREDENTIALS: ErrorSpec(401, "Credenciales MCP inválidas"),
    ErrorCode.NOT_OWNER: ErrorSpec(403, "No tenés acceso a este recurso"),
    ErrorCode.ADMIN_ONLY: ErrorSpec(403, "Esta operación requiere rol administrador"),
    ErrorCode.RATE_LIMITED: ErrorSpec(429, "Muchos intentos, esperá un momento"),
    ErrorCode.DISK_FULL: ErrorSpec(507, "No hay espacio suficiente para completar la operación"),
    ErrorCode.INTERNAL_ERROR: ErrorSpec(500, "Algo salió mal, revisá los logs"),
}


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        *,
        message: str | None = None,
        http_status: int | None = None,
    ) -> None:
        spec = ERROR_CATALOG[code]
        self.code = code
        self.message = message or spec.message
        self.http_status = http_status or spec.http_status
        super().__init__(self.message)

    def to_payload(self, request_id: str | None = None) -> dict[str, str | None]:
        return {
            "code": self.code.value,
            "message": self.message,
            "request_id": request_id,
        }


def payload_for_code(code: ErrorCode, request_id: str | None = None) -> dict[str, str | None]:
    spec = ERROR_CATALOG[code]
    return {"code": code.value, "message": spec.message, "request_id": request_id}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=exc.http_status, content=exc.to_payload(request_id))


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled application error", exc_info=exc)
    spec = ERROR_CATALOG[ErrorCode.INTERNAL_ERROR]
    return JSONResponse(
        status_code=spec.http_status,
        content=payload_for_code(ErrorCode.INTERNAL_ERROR, request_id=request_id),
    )
