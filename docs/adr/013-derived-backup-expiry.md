# Derived backup expiry

## Status

Accepted. CCR [#135](https://github.com/carloshugoeg/koicloud/issues/135).

## Context

The backups table needs an **Expira** column filled from the API. `backups` has no `expires_at` column, and inventing retention in the browser violates the thin-surface rule. Plan-level retention (`PlanOut.backup_retention_days`, A3 / #124) is not on `main` yet.

## Decision

`BackupOut.expires_at` is derived when serializing:

- `null` if `status != succeeded` or `kind == pre_delete`
- otherwise `created_at + BACKUP_RETENTION_DAYS` (7 days, UTC)

No migration. Constant lives in `apps/api/app/modules/backups/retention.py` until plan retention lands.

## Consequences

Web can show `en N d` / `hoy` / `vencido` without client-side math. When A3 lands, swap the constant for `PlanOut.backup_retention_days` without another schema change.
