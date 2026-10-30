from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.enums import BackupKind, BackupStatus
from app.core.models import Backup
from app.modules.backups.retention import BACKUP_RETENTION_DAYS, expires_at_for
from app.modules.backups.service import backup_to_out

CREATED = datetime(2026, 9, 22, 20, 0, tzinfo=UTC)


def _backup(kind: BackupKind, status: BackupStatus, created_at: datetime = CREATED) -> Backup:
    return Backup(
        id=uuid4(),
        pond_id=uuid4(),
        kind=kind,
        status=status,
        storage_path="/var/lib/koicloud/backups/demo.dump",
        created_at=created_at,
    )


def test_retention_constant_is_seven_days() -> None:
    assert BACKUP_RETENTION_DAYS == 7


def test_succeeded_daily_and_on_demand_expire_seven_days_later() -> None:
    expected = CREATED + timedelta(days=7)
    assert expires_at_for(_backup(BackupKind.DAILY, BackupStatus.SUCCEEDED)) == expected
    assert expires_at_for(_backup(BackupKind.ON_DEMAND, BackupStatus.SUCCEEDED)) == expected


def test_pre_delete_has_no_expiry_even_when_succeeded() -> None:
    assert expires_at_for(_backup(BackupKind.PRE_DELETE, BackupStatus.SUCCEEDED)) is None


@pytest.mark.parametrize(
    "status",
    [BackupStatus.QUEUED, BackupStatus.RUNNING, BackupStatus.FAILED],
)
def test_backup_without_success_has_no_expiry(status: BackupStatus) -> None:
    assert expires_at_for(_backup(BackupKind.DAILY, status)) is None


def test_naive_created_at_is_treated_as_utc() -> None:
    backup = _backup(
        BackupKind.DAILY,
        BackupStatus.SUCCEEDED,
        created_at=datetime(2026, 9, 22, 20, 0),
    )
    assert expires_at_for(backup) == datetime(2026, 9, 29, 20, 0, tzinfo=UTC)


def test_backup_to_out_copies_derived_expires_at() -> None:
    out = backup_to_out(_backup(BackupKind.DAILY, BackupStatus.SUCCEEDED))
    assert out.expires_at == CREATED + timedelta(days=BACKUP_RETENTION_DAYS)
    queued = backup_to_out(_backup(BackupKind.ON_DEMAND, BackupStatus.QUEUED))
    assert queued.expires_at is None
