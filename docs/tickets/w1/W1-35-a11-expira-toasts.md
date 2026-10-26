---
id: W1-35
workstream: W1
persona: Carlos
estado: bloqueado
rama: w1-a11-expira-toasts
epica: "#96 A11"
sprint:
pr: "https://github.com/carloshugoeg/koicloud/pull/134"
depends_on:
ccr: "https://github.com/carloshugoeg/koicloud/issues/135"
---

# [W1-35] Columna Expira y toasts de 1.2 s

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96), enmienda A11.

**BLOQUEADO: requiere CCR porque** `BackupOut.expires_at` es schema OpenAPI congelado.
CCR abierto: [#135](https://github.com/carloshugoeg/koicloud/issues/135). El código del feature permanece en PR [#134](https://github.com/carloshugoeg/koicloud/pull/134) hasta que Carlos apruebe el CCR. **No mergear.**

**Renumber:** antes mal etiquetado `W1-27` (ese id lo tiene [#123](https://github.com/carloshugoeg/koicloud/pull/123) plans pricing).

**Coordinación Wave A2** (`w2-a2-web-gaps` / W2-15, agent `bc-886f398c`): A2 es dueño de toasts first-party, Respaldar ahora / Reintentar UI, y deja Expira en «—» sin tocar contratos. Este PR (W1) aporta el campo API derivado + relleno de Expira. Tras CCR + merge de A2, unificar toast host si ambos aterrizan (evitar dos buses).

## Qué se ve

La tabla de respaldos llena **Expira** con `en N d`, `hoy`, `vencido` o `—`, según `expires_at`. Toast de 1.2 s para URI / respaldo / reintento. **Respaldar ahora** y **Reintentar** contra POST existentes.

## Entradas ya decididas (no se cambian)

- `BackupOut.expires_at` derivado; sin migración. Ver CCR #135.
- `expires_at_for(backup)` en `apps/api/app/modules/backups/retention.py`. `BACKUP_RETENTION_DAYS = 7`.
- null si no `succeeded` o `pre_delete`; si no, `created_at` + 7 días UTC.
- Wave A2 puede ya cubrir toast + retry/backup-now en web; no duplicar ese trabajo en un segundo PR web-only.

## Criterios de aceptación

1. Tras CCR aprobado: `GET /ponds/{id}/backups` trae `expires_at` según la regla del CCR.
2. Columna **Expira** no queda siempre en `—` cuando hay timestamp.
3. Toast 1200 ms (si este PR mantiene el host; preferir el de A2 si ya merged).
4. `make check-api` y `make check-web` pasan.
5. Sin merge hasta CCR #135 aprobado.

## No tocar

- Migraciones Alembic.
- Firmas de `app/commands/*`.
- Stop/start (A5) y motivo de suspensión (#121).
- Editar OpenAPI a mano.

## Si algo falta

Respondé `BLOQUEADO: requiere CCR porque …` y pará.

## Referencia

CCR [#135](https://github.com/carloshugoeg/koicloud/issues/135) · PR [#134](https://github.com/carloshugoeg/koicloud/pull/134) · Wave A2 W2-15.
