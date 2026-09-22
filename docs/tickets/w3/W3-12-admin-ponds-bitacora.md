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
- Los filtros y query params exactos no están cerrados en el store.
- Los schemas deben dejar `example` suficiente para Web admin.

## Criterios de aceptación

1. `GET /admin/ponds` devuelve rows de todo el sistema con dueño y estado.
2. `GET /admin/audit` devuelve actor, acción, target, timestamp y metadata.
3. Los endpoints se mantienen read-only y sin helpers ocultos de mutación.
4. Hay pruebas de API para filtros/paginación una vez que W1 congele los query params.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.
- Si W1 no define los query params exactos de filtros/paginación, bloqueá y no inventes `?user_id=` o `?state=` por tu cuenta.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
