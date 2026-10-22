---
id: W1-22
workstream: W1
persona: Carlos Hugo Escobar
estado: abierto
rama: w1-job-transitions-ocp
epica: E4-04
sprint: S5
pr:
depends_on: W1-21
---

# [W1-22] Transiciones de job explícitas (OCP)

## Qué se ve

Al completar un job, el estado observado del pond (y backups encadenados) no cambia para el usuario. En código, `JobService.complete` deja de ser una cadena `if/elif` por tipo: una tabla o registro de handlers por `JobType` aplica la transición. Añadir un tipo nuevo no edita el cuerpo de `complete`.

## Entradas ya decididas (no se cambian)

- Máquina de estados de `docs/architecture/data-model.md` § ponds/jobs (observed/desired).
- Endpoints internos `claim` / `complete` / heartbeat; firmas de `commands/internal.py`.
- Cadena `PRE_DELETE` backup → encolar `DELETE_POND` (comportamiento actual).
- Depende de W1-21 para el touch de nodo unificado (`depends_on`).

## Criterios de aceptación

1. `complete()` despacha por registro/tabla de transiciones; no hay `elif job.type ==` creciendo en el método.
2. Casos actuales cubiertos con pruebas: create/start → running; delete → deleted; backup ok/fail; restore → running + `last_restore_at`; pre_delete → encola delete.
3. Heartbeat/claim siguen usando el touch de nodo de W1-21 (sin copia local divergente).
4. `make check-api` verde; sin CCR de OpenAPI.

## No tocar

- Firmas de comandos, OpenAPI, migraciones.
- Drivers del node-agent (solo control plane).
- `apps/web/**`, `apps/cli/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- `docs/architecture/solid-review.md` § jobs
- `apps/api/app/modules/jobs/service.py` (`complete`, `_complete_backup`)
