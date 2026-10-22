---
id: W1-21
workstream: W1
persona: Carlos Hugo Escobar
estado: abierto
rama: w1-pond-service-srp
epica: E3-01
sprint: S5
pr:
depends_on:
---

# [W1-21] Partir `PondService` (SRP / DIP)

## Qué se ve

Tras el cambio, crear/listar/borrar ponds sigue respondiendo igual en HTTP. En código, `PondService` ya no upserta usuarios, no inventa suscripciones Micro ni toca nodos: esas responsabilidades viven en colaboradores inyectados o módulos propios. Un solo camino actualiza `nodes` (compartido con jobs).

## Entradas ya decididas (no se cambian)

- Firmas de `app/commands/ponds.py` (contrato congelado).
- Tablas/enums de `docs/architecture/data-model.md` (sin migración salvo CCR).
- Comportamiento observable de `POST /ponds`, cuota `quota_exceeded`, `NODE_UNAVAILABLE`, auto Micro vía setting existente `auto_micro_subscription`.
- Hallazgo documentado en `docs/architecture/solid-review.md` § ponds.

## Criterios de aceptación

1. `PondService` no define `ensure_actor`, `ensure_subscription` ni `_upsert_node`; delega a colaboradores con tests unitarios propios.
2. Un solo helper/servicio de nodo lo usan ponds y jobs (mismo semántica de `last_seen_at` / `ALIVE` documentada en el PR).
3. `delete` no importa `BackupService` en línea media del método: dependencia explícita (ctor o puerto) sin cambiar el flujo pre_delete → delete.
4. `make check-api` verde; sin cambios a OpenAPI ni firmas de comandos.

## No tocar

- `packages/contracts/**`, firmas de `app/commands/*`, migraciones Alembic.
- `apps/web/**`, `apps/cli/**`.
- Facturación más allá de leer suscripción activa / auto Micro ya existente.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- `docs/architecture/solid-review.md` § ponds
- PR de persistencia de ponds [#6](https://github.com/carloshugoeg/koicloud/pull/6)
