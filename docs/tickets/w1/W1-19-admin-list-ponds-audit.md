---
id: W1-19
workstream: W1
persona: Carlos
estado: en_revision
rama: w3-admin-ponds-bitacora
epica: "E8-02, E8-04"
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/82
---

# [W1-19] Wire admin_list_ponds / admin_list_audit to AdminService

## Qué se ve

Los comandos congelados `admin_list_ponds` y `admin_list_audit` dejan de devolver
`.example()` y delegan en `AdminService` (W3), que lee ponds y `audit_events` de la DB.

## Entradas ya decididas (no se cambian)

- Firmas de comando sin parámetros ni cambios de retorno.
- OpenAPI sin cambios (sin `limit`/`offset`).
- Acciones de bitácora: `suspend_user`, `reveal_agent_access`, `delete_pond`, `restore_backup`.

## Criterios de aceptación

1. `admin_list_ponds` / `admin_list_audit` llaman a `AdminService` (no fixtures).
2. Sin edits a `packages/contracts/**` ni a firmas de comando.
3. Cubierto por las pruebas de W3-12 en el mismo PR (label `cross-workstream`).

## No tocar

- `packages/contracts/**`.
- Firmas de otros comandos.
- Alembic / data-model.

## Si algo falta

Respondé `BLOQUEADO: requiere CCR porque …` y pará.

## Referencia

Mismo patrón que `commands/ponds.list_ponds` → `PondService`.
