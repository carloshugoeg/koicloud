---
id: W3-11
workstream: W3
persona: Jousé
estado: abierto
rama: w3-admin-usuarios
epica: "E8-01, E8-03"
sprint: S4
pr:
---

# [W3-11] Admin: usuarios, suspender y reactivar

## Qué se ve

Superficie backend para la tabla de usuarios admin y las acciones de suspender/reactivar. Lo visible es el contrato admin-only y el cambio de estado del usuario.

## Entradas ya decididas (no se cambian)

- Endpoints: `GET /admin/users`, `POST /admin/users/{id}/suspend`, `POST /admin/users/{id}/reactivate`.
- Guard fijo: `admin_only`.
- Suspender bloquea login y mata sesión activa, pero no detiene ponds ni borra datos.
- El listado incluye `active_plan_id` y `pond_count`.
- La confirmación en Web es textual/expresa; aquí no se rediseña ese UX.

## Criterios de aceptación

1. La lista admin pagina usuarios con plan y cantidad de ponds.
2. Suspender marca `suspended_at` y deja datos suficientes para la UI/admin audit.
3. Reactivar limpia el estado de suspensión.
4. Un usuario no admin recibe `admin_only`.
5. Hay pruebas de API para suspender/reactivar y para login bloqueado estando suspendido.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
