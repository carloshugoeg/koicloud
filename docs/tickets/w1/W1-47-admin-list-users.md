---
id: W1-47
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-g02-admin-users
epica: E8-01
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/183
depends_on: W1-15 W1-19 W3-11
---

# [W1-47] El listado admin de usuarios lee la base

## Qué se ve

Administración → Usuarios muestra las cuentas reales de `users` (correo, nombre, plan activo, estado). Buscar filtra esas cuentas. Suspender y reactivar actúan sobre ellas. El build de producción no incluye el worker de MSW ni cuentas de fixture.

## Entradas ya decididas (no se cambian)

- Firma de `admin_list_users()` sin parámetros. Retorno `AdminUserListResponse`.
- `GET /api/v1/admin/users` ya existe. Guard `admin_only`.
- Campos de `AdminUserOut`: `active_subscription_plan` es el plan de la suscripción activa, o null.
- `next_cursor` sigue en null, igual que ponds y suscripciones en v0.
- Suspender y reactivar ya persisten. Este ticket no cambia su firma.
- El conteo de ponds de la tabla web se sigue calculando con `GET /admin/ponds`.

## Criterios de aceptación

1. Tras registrar `qa-admin@koicloud.test` y `qa+1@koicloud.test`, `GET /admin/users` devuelve exactamente esas cuentas y no `carlos@koicloud.dev` ni `suspended@koicloud.dev`. Prueba `test_admin_list_users_returns_registered_accounts_not_fixtures`.
2. La pantalla de usuarios, con MSW apagado y una respuesta de red, pinta esas cuentas. Prueba `admin users from the API client with MSW off` / `renders the accounts returned by the network`.
3. El buscador deja solo las cuentas cuyo correo o nombre contiene el texto. Prueba `filters those accounts by the search box`.
4. `vite build` de producción, sin `VITE_ENABLE_MOCKS`, no deja `mockServiceWorker.js` ni textos de fixture en `dist`. Prueba `vite production build ships no mock worker and no fixture accounts`.

## No tocar

- `packages/contracts/**` y `apps/web/src/api/schema.d.ts`.
- Firmas de `app/commands/*`.
- Tablas, columnas y enums.
- `.github/workflows/deploy.yml`.

## Si algo falta

Respondé `BLOQUEADO: requiere CCR porque …` y pará. La firma ya existe. El cuerpo del comando es el que estaba fijo.

## Referencia

Mismo patrón que `admin_list_ponds` en W1-19: el comando lee la base a través de los helpers que ya usan suspender y reactivar.
