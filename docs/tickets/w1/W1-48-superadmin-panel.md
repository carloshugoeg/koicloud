---
id: W1-48
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-superadmin-panel
epica: E8-01
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/228
depends_on:
---

# [W1-48] Panel superadmin: cuentas con plan, verificado, creado y ponds

## Qué se ve

Administración → Usuarios lista todas las cuentas con correo, plan activo, estado
verificado, fecha de creación y cantidad de ponds. La paginación por cursor no cambia.
El enlace de Administración sigue visible solo para `role=admin`. Un no-admin recibe
`403 admin_only`; anónimo, `401`. La respuesta no incluye hashes, tokens ni secretos.

## Entradas ya decididas (no se cambian)

- Extiende `GET /api/v1/admin/users` y `/app/admin/users` de W1-47 / PR #183. No hay
  panel paralelo ni ruta nueva.
- Guard: `get_admin_user` / `UserRole.ADMIN`. Sin nuevo enum ni migración de roles.
- `AdminUserOut` ya tiene `email`, `active_subscription_plan`, `email_verified`,
  `created_at`. Se agrega `ponds_count: int` (conteo derivado de `ponds.user_id`,
  mismo universo que `GET /admin/ponds`: todas las filas del owner).
- Cursor `limit`/`next_cursor` sin cambio de semántica.
- Contratos: `make contracts` regenera `packages/contracts/openapi.json` y
  `apps/web/src/api/schema.d.ts`. Changelog en `packages/contracts/CHANGELOG.md`.
- UI en español; columnas nuevas «Verificado» y «Creado» en `users-table.tsx`.
- Rama: `w1-superadmin-panel`. Base del PR: `w1-g02-admin-users`.

## Criterios de aceptación

1. Admin autenticado: `GET /admin/users` 200 con `email`, `active_subscription_plan`,
   `email_verified`, `created_at`, `ponds_count` y sin campos secretos. Prueba
   `test_admin_list_users_superadmin_panel_fields`.
2. No-admin: 403 `admin_only`. Prueba `test_admin_list_users_non_admin_forbidden_for_panel`.
3. Anónimo: 401 `token_invalid`. Prueba `test_admin_list_users_anonymous_receives_401`.
4. La tabla web muestra columnas Verificado y Creado (y Plan / Ponds). Prueba
   `renders verified and created columns on the users table`.
5. El nav Administración solo aparece para `role=admin` (comportamiento existente).

## No tocar

- Stack MCP / temp-access (#224–#226).
- Stack de schema de ponds (#213 / #214).
- Nuevos roles en el enum `user_role`.
- Migraciones Alembic.
- Deploy, prod/staging, servicios de pago nuevos.

## Si algo falta

Respondé `BLOQUEADO: requiere CCR porque …` solo si hace falta editar algo fuera de
este ticket (p. ej. un campo no derivado). Carlos aprueba el campo `ponds_count` en
este ticket.

## Referencia

W1-47 (`docs/tickets/w1/W1-47-admin-list-users.md`) · W1-34 (campo derivado +
`make contracts`) · PR #183.
