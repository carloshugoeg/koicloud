---
id: W1-27
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-pond-stop-start
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/130"
depends_on: W1-17 W1-10
---

# [W1-27] Pond stop / start + delete with backup first

## Qué se ve

El usuario puede **detener** y **arrancar** un pond, y **borrarlo** siempre con respaldo
`pre_delete` antes del `delete_pond`. La máquina de estados acordada es el diagrama TLC
`docs/architecture/diagrams/20-pond-lifecycle-stop-start-delete.mmd` (PNG al lado; spec en
`docs/architecture/statecharts/pond-lifecycle/`).

- `POST /api/v1/ponds/{id}/stop` → `desired=stopped`, job `stop_pond` queued, 202.
- `POST /api/v1/ponds/{id}/start` → `desired=running`, job `start_pond` queued, 202.
- `DELETE /api/v1/ponds/{id}` sigue encolando solo `backup_pond` `kind=pre_delete`; al
  completar con éxito, `JobService` encola `delete_pond`. Nunca se borra el contenedor
  sin ese respaldo.

CLI/MCP: stop/start/delete pasan por `propose → confirm`. Web: sin token de confirmación.

## Entradas ya decididas (no se cambian)

- Diagrama acordado: `20-pond-lifecycle-stop-start-delete` (invariantes TLC verdes:
  GoneWhileWantedOn/Off, Online/OfflineAfterYouRemovedIt, GoneOnlyWhenRemoved).
- Enums ya en `main`: `PondDesiredState.stopped`, `JobType.start_pond|stop_pond`,
  `BackupKind.pre_delete`. Handlers node-agent `start_pond` / `stop_pond` ya existen.
- Errores del catálogo: `pond_not_found`, `pond_busy`. Stop solo con `observed=running`.
  Start solo con `observed=stopped`.
- `jobs_one_active` sigue: un solo job `queued|running` por pond.
- Reconciler: no encola delete/backup para `desired=deleted` + `observed=running|stopped`
  (sigue mandando el pre_delete de `PondService.delete`). Añade remediación
  `(stopped, running) → stop_pond` no aplica (desired stopped + observed running es el
  gap corto tras el POST; el job ya está encolado). Remedia
  `(running, stopped) → start_pond` (ya existe) y
  `(stopped, running)` no: el POST stop ya encoló el job.
- **CCR requerido** para rutas OpenAPI nuevas y firmas `stop_pond` / `start_pond` en
  `commands/ponds.py`, más filas en `api-surface.md` y el matiz “fuera de MVP” en
  `data-model.md` §4.1. Sin CCR aprobado no se regenera el contrato.

## Criterios de aceptación

1. Diagrama `20-pond-lifecycle-stop-start-delete` + PNG + spec TLC en el PR **antes** del
   código de producto; invariantes del summary en verde.
2. `POST .../stop` con pond `running` → 202 `{pond, job}` con `desired_state=stopped` y
   job `stop_pond` `queued`. Complete succeeded → `observed_state=stopped`.
3. `POST .../start` con pond `stopped` → 202 con `desired_state=running` y job
   `start_pond`. Complete succeeded → `observed_state=running`.
4. Stop con observed ≠ `running` → error del catálogo (`pond_busy` o el código CCR
   acordado). Start con observed ≠ `stopped` → igual. Job activo → `409 pond_busy`.
5. `DELETE` encola `pre_delete` backup primero; solo tras backup succeeded aparece
   `delete_pond`. Fallo de pre_delete deja `desired=deleted`, `observed=deleting` (o
   failed hold según diagrama) **sin** destruir el contenedor.
6. CLI/MCP stop/start/delete sin confirm token → `409 confirmation_required` con summary
   en español.
7. Pruebas API + node-agent mock verdes; `make check-api` y `make check-node-agent` pasan.
8. Un solo archivo de ticket (`W1-27`). Ningún cambio de contrato congelado sin CCR
   enlazado en el PR.

## No tocar

Migraciones Alembic nuevas (enums ya existen). Billing. Pantallas W2 salvo el cableado
mínimo de botones si el CCR de rutas ya está aprobado y el ticket lo pide en un follow-up.
No inventar códigos de error fuera del catálogo / CCR.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

`docs/architecture/diagrams/20-pond-lifecycle-stop-start-delete.mmd`,
`docs/architecture/statecharts/pond-lifecycle/`, `W1-17` reconciler, `W1-10` backups,
`PondService.delete` + `JobService._complete_backup`.
