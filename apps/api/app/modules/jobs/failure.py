from __future__ import annotations

import logging
from uuid import UUID

from koicloud_job_sanitize import log_text, redact

from app.core.enums import JobType
from app.core.sentry import capture_job_failure

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


def _public(code: str) -> str:
    return f"{code}: {_MESSAGES[code]}"


def _classify(job_type: JobType, raw: str) -> str:
    head = raw.split(":", 1)[0].strip()
    if head == "dump_failed":
        return "backup_failed"
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


def report_failure(
    job_id: UUID,
    raw: str | None,
    *,
    pond_id: UUID | None = None,
    code: str | None = None,
) -> None:
    if code is None:
        head = (raw or "").split(":", 1)[0].strip()
        if head in {"dump_failed", "pg_dump"} or head.startswith("pg_dump"):
            code = "backup_failed"
        elif head == "psql" or head.startswith("psql"):
            code = "restore_failed"
        elif head in _MESSAGES:
            code = head
        elif head:
            code = head
        else:
            code = "job_failed"
    diagnostic = log_text(raw or "")
    logger.error("job %s failed: %s", job_id, diagnostic)
    capture_job_failure(code=code, job_id=job_id, pond_id=pond_id)


__all__ = [
    "for_client",
    "public_failure",
    "redact",
    "report_failure",
]
