from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.enums import BackupKind, BackupStatus
from app.core.models import Backup

BACKUP_RETENTION_DAYS = 7


def expires_at_for(backup: Backup) -> datetime | None:
    if backup.status != BackupStatus.SUCCEEDED or backup.kind == BackupKind.PRE_DELETE:
        return None
    created_at = backup.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return created_at + timedelta(days=BACKUP_RETENTION_DAYS)
