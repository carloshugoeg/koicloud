from __future__ import annotations

from app.modules.billing.plan_retention import (
    PLAN_BACKUP_RETENTION_DAYS,
    backup_retention_days_for,
)


def test_seeded_plan_retention_days() -> None:
    assert backup_retention_days_for("sandbox") == 0
    assert backup_retention_days_for("micro") == 7
    assert backup_retention_days_for("pro") == 30
    assert PLAN_BACKUP_RETENTION_DAYS["micro"] == 7


def test_unknown_plan_defaults_to_zero() -> None:
    assert backup_retention_days_for("unknown-plan") == 0
