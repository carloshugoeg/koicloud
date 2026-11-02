from __future__ import annotations

import logging
import os
import re
from uuid import UUID

from app.core.enums import JobType

logger = logging.getLogger(__name__)

_MESSAGES: dict[str, str] = {
    "restore_failed": "No se pudo restaurar el pond.",
    "backup_failed": "No se pudo crear el respaldo.",
    "backup_not_found": "No se encontró el respaldo.",
    "create_failed": "No se pudo crear el pond.",
    "start_failed": "No se pudo iniciar el pond.",
    "stop_failed": "No se pudo detener el pond.",
    "delete_failed": "No se pudo eliminar el pond.",
    "pond_not_found": "No se encontró el pond en el nodo.",
    "pond_not_ready": "El pond no estuvo listo a tiempo.",
    "pond_name_taken": "Ese nombre de pond ya está en uso.",
    "disk_full": "No hay espacio suficiente para completar la operación.",
    "job_failed": "No se pudo completar la operación.",
}

_BY_TYPE: dict[JobType, str] = {
    JobType.RESTORE_POND: "restore_failed",
    JobType.BACKUP_POND: "backup_failed",
    JobType.CREATE_POND: "create_failed",
    JobType.START_POND: "start_failed",
    JobType.STOP_POND: "stop_failed",
    JobType.DELETE_POND: "delete_failed",
}

_PUBLIC = {f"{code}: {message}" for code, message in _MESSAGES.items()}

_URI_PASSWORD = re.compile(r"(://[^\s/:@]+:)[^\s/@]+@")
_SECRET_ASSIGN = re.compile(r"(?i)\b(password|passwd|pwd|secret|token)\b\s*[=:]\s*\S+")
_DATA_LINE = re.compile(r"(?i)^\s*(INSERT\b|COPY\b|UPDATE\b|DELETE\b)")


def _public(code: str) -> str:
    return f"{code}: {_MESSAGES[code]}"


def _classify(job_type: JobType, raw: str) -> str:
    head = raw.split(":", 1)[0].strip()
    if head in _MESSAGES and head != "job_failed":
        return head
    return _BY_TYPE.get(job_type, "job_failed")


def public_failure(job_type: JobType, raw: str | None) -> str:
    return _public(_classify(job_type, raw or ""))


def for_client(stored: str | None) -> str | None:
    if stored is None:
        return None
    if stored in _PUBLIC:
        return stored
    return _public("job_failed")


def redact(raw: str) -> str:
    kept: list[str] = []
    for line in raw.splitlines():
        if _DATA_LINE.match(line):
            kept.append("[redacted]")
            continue
        line = _URI_PASSWORD.sub(r"\1[redacted]@", line)
        line = _SECRET_ASSIGN.sub(lambda match: f"{match.group(1)}=[redacted]", line)
        kept.append(line)
    return "\n".join(kept)


def report_failure(job_id: UUID, raw: str | None) -> None:
    redacted = redact(raw or "")
    logger.error("job %s failed: %s", job_id, redacted)
    _capture_sentry(f"job {job_id} failed: {redacted}")


def _capture_sentry(message: str) -> None:
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return
    import sentry_sdk

    if not sentry_sdk.is_initialized():
        sentry_sdk.init(dsn=dsn, send_default_pii=False)
    sentry_sdk.capture_message(message, level="error")
