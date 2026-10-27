---
id: W1-35
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-a11-expira-toasts
epica: "#96 A11"
sprint:
pr: "https://github.com/carloshugoeg/koicloud/pull/134"
depends_on:
ccr: "https://github.com/carloshugoeg/koicloud/issues/135"
---

# [W1-35] Columna Expira y toasts de 1.2 s

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96), enmienda A11.

CCR [#135](https://github.com/carloshugoeg/koicloud/issues/135) **aprobado** (amendment r3, 2026-10-27). Implementado en PR [#134](https://github.com/carloshugoeg/koicloud/pull/134). **No mergear** hasta ship-review.

**Renumber:** antes mal etiquetado `W1-27` (ese id lo tiene [#123](https://github.com/carloshugoeg/koicloud/pull/123) plans pricing).

**Coordinación Wave A2** (`w2-a2-web-gaps` / W2-15): A2 es dueño de toasts first-party, Respaldar ahora / Reintentar UI. Este PR aporta el campo API derivado + relleno de Expira.

## Qué se ve

La tabla de respaldos llena **Expira** con `en N d`, `hoy`, `vencido` o `—`, según `expires_at`. Toast de 1.2 s para URI / respaldo / reintento. **Respaldar ahora** y **Reintentar** contra POST existentes.

## Entradas ya decididas (no se cambian)

- `BackupOut.expires_at` derivado; sin migración. Ver CCR #135.
- `expires_at_for(backup)` en `apps/api/app/modules/backups/retention.py`. `BACKUP_RETENTION_DAYS = 7`.
- null si no `succeeded` o `pre_delete`; si no, `created_at` + 7 días UTC.
- No tocar `PlanOut.backup_retention_days` (#123 / #124).

## Criterios de aceptación

1. `GET /ponds/{id}/backups` trae `expires_at` según la regla del CCR.
2. Columna **Expira** no queda siempre en `—` cuando hay timestamp.
3. Toast 1200 ms (si este PR mantiene el host; preferir el de A2 si ya merged).
4. `make check-api` y `make check-web` pasan.
5. Contratos regenerados (`make contracts`).

## No tocar

- Migraciones Alembic.
- Firmas de `app/commands/*`.
- `PlanOut` / pricing (#123) / `backup_retention_days` (#124).
- Stop/start (A5) y motivo de suspensión (#121).
- Editar OpenAPI a mano.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque …` y pará solo si hay que *editar* un contrato congelado o un archivo ajeno.

## Referencia

CCR [#135](https://github.com/carloshugoeg/koicloud/issues/135) · PR [#134](https://github.com/carloshugoeg/koicloud/pull/134).
