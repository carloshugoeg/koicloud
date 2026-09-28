---
id: W3-12
workstream: W3
persona: Jousé
estado: abierto
rama: w3-admin-ponds-bitacora
epica: "E8-02, E8-04"
sprint: S4
pr:
---

# [W3-12] Admin: ponds del sistema y bitácora

## Qué se ve

Endpoints read-only para ver ponds de todo el sistema y la bitácora sensible. Lo visible es un feed admin con ownership global y acciones auditables selladas.

## Entradas ya decididas (no se cambian)

- Endpoints: `GET /admin/ponds` y `GET /admin/audit`.
- La bitácora solo muestra acciones `suspend_user`, `reveal_agent_access`, `delete_pond` y `restore_backup`.
- La lectura es global para admins; no hay mutaciones aquí.
- Query params congelados (solo estos): `limit` (default 50, max 100) y `offset`
  (default 0). Sin `user_id`, `state` ni otros filtros en v0.
- Comandos: `admin_list_ponds` y `admin_list_audit`. Call only.
- Los schemas deben dejar `example` suficiente para Web admin.

## Criterios de aceptación

1. `GET /admin/ponds` devuelve rows de todo el sistema con dueño y estado.
2. `GET /admin/audit` devuelve actor, acción, target, timestamp y metadata.
3. Los endpoints se mantienen read-only y sin helpers ocultos de mutación.
4. Hay pruebas de API para `limit`/`offset` (página 2 vacía si no hay filas).

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO` si el ticket pidiera un filtro que no está en *Entradas*.
`limit`/`offset` ya están. No inventes `?user_id=` ni `?state=`.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
