"""Catalog backup retention for GET /plans (issue #96 A3).

Kept as a server-side map — plans has no retention column.
"""

from __future__ import annotations

# Days of automatic daily backup retention by plan id.
# 0 = no automatic backups (matches catalog copy "No").
PLAN_BACKUP_RETENTION_DAYS: dict[str, int] = {
    "sandbox": 0,
    "micro": 7,
    "pro": 30,
}


def backup_retention_days_for(plan_id: str) -> int:
    """Return retention days for a plan id; unknown ids default to 0."""
    return PLAN_BACKUP_RETENTION_DAYS.get(plan_id, 0)
