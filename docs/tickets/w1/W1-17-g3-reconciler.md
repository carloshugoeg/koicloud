---
id: W1-17
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-g3-reconciler
epica: E4-05
sprint: S3
pr: "https://github.com/carloshugoeg/koicloud/pull/53"
depends_on:
---

# [W1-17] Reconciler mínimo (G3 / E4-05)

## Qué se ve

Un proceso worker corre `python -m app.workers.reconciler` cada 30 s. Si un pond tiene
`desired ≠ observed` y no hay job `queued`/`running`, encola el job de corrección remediable
(por ejemplo `start_pond` cuando `desired=running` y `observed=stopped`). Jobs `running` con
`claimed_at` más viejo que 2 minutos pasan a `lost` y se reencolan mientras `attempts < 3`.
No se vende como auto-heal.

## Entradas ya decididas (no se cambian)

- Diagrama `docs/architecture/diagrams/09-reconciler-heartbeat.mmd` e interconnections §5–§6.
- Enums `JobType` / `JobStatus` (incluye `lost`) y índice `jobs_one_active` ya en `main`.
- `ClaimedJobPayload` exige `name`, `host_port`, `memory_mb`, `cpus`, `db_password_plain`, `image`.
- Payload de agente: mismos defaults que `PondService._agent_payload` (512 MB, 0.5 CPU, `postgres:16-alpine`).
- **pre_delete-safe:** `desired=deleted` + `observed=running|stopped` is **not remediable** in the
  reconciler (no-op). `PondService.delete` owns the pre_delete `backup_pond` → then `delete_pond`.
  Do not enqueue backup or delete from the reconciler for those pairs.
- `desired=deleted` + `observed=deleting` is a hold unless the latest job is a failed `delete_pond`
  (failed pre_delete backup must not unlock delete).
- `_resolve_job_type` stays: on `running`+`failed`, retry the last failed type when it is
  `create_pond` / `start_pond` / `delete_pond` so a failed `start_pond` is retried instead of
  always falling back to `create_pond`. Never replay backup/restore from drift.
- Drift requeues carry `attempts` from the prior failed row of the same type (claim increments).

## Criterios de aceptación

1. Worker long-lived con intervalo 30 s y `pg_try_advisory_lock` por tick.
2. Drift remediable sin job activo → inserta un job `queued` con payload claimable.
3. Zombie `running` (`claimed_at` > 2 min) → `lost` → requeue si `attempts < 3`, si no `failed`.
4. El reconciler no muta `ponds.desired_state` ni `pond_status.observed_state`.
5. `JobService.complete` con `start_pond` succeeded deja `observed=running` (convergencia).
6. Compose `worker` ejecuta `python -m app.workers.reconciler`.
7. `pytest tests/test_reconciler.py` verde.

## No tocar

`apps/web/**`, `modules/billing/**`, OpenAPI/schemas congelados, migraciones nuevas.

## Si algo falta

Si hace falta editar un contrato congelado → `BLOQUEADO`. Heartbeat aún no escribe
`observed=stopped`; ese cableado es otro ticket. Este PR deja el remediable listo.

## Referencia

`apps/api/app/workers/daily_backups.py`, `PondService.retry_failed`, diagrama 09.
