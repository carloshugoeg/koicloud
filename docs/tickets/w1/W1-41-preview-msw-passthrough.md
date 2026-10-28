---
id: W1-41
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-preview-msw-passthrough
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/156"
depends_on: W1-40
---

# [W1-41] Preview MSW passthrough for seeded gate admin

**HIGH lane** (auth path / MSW login + session). Waits Carlos’s 9:00 / 16:00
`America/Guatemala` window — do **not** merge outside that window. Unblocks gate
walks on #132 Preview while `VITE_ENABLE_MOCKS=true` stays on for the SPA demo.

Supersedes the failed attempt on [#155](https://github.com/carloshugoeg/koicloud/pull/155)
(`cursor/…` branch failed ownership).

## Qué se ve

On Vercel **Preview** with MSW enabled:

1. Login with the **seeded** gate admin (Preview DB, not MSW fixtures) hits
   `POST /api/v1/auth/login` on the **real** Preview API → `200` with
   `role=admin` and a real JWT.
2. Subsequent authenticated calls (`/admin/**`, `/me`, …) that carry that JWT
   also hit the **real** Preview API — MSW does not answer them with fixtures.
3. Demo emails (`demo@koicloud.dev`, `admin@koicloud.dev`) and demo Bearer
   tokens (`access_demo_token`, `access_admin_token`, `access_refreshed_token`)
   still get MSW fixtures for local/Vitest demos.

## Entradas ya decididas (no se cambian)

- `VITE_ENABLE_MOCKS=true` remains Preview-only; production still forbids it.
- Seed credentials live only in Vercel Preview env + Agent Store path for #132;
  never in client bundle, PR body, or chat.
- No OpenAPI / command signature / migration changes.
- Branch must be `w1-preview-msw-passthrough` (ownership: `w1-`…`w4-` prefix).

## Criterios de aceptación

1. `getResponse(handlers, loginRequest)` for `gate-132-admin@koicloud.test`
   returns MSW passthrough (`x-msw-intention: passthrough`) — asserted directly
   in `preview-passthrough.test.ts`.
2. Same suite: `Authorization: Bearer <non-demo JWT>` on `/api/v1/admin/users`
   is passthrough; `Bearer access_admin_token` still returns the MSW users list.
3. Demo `demo@koicloud.dev` login still returns `access_demo_token` (existing
   auth tests stay green).
4. Ticket `estado` + INDEX row match the PR lifecycle (`en-revision` while open).

## No tocar

- `apps/api/**` (except read-only imports if any — none expected)
- `packages/contracts/**`, Alembic, OpenAPI
- Vercel Production env vars
- Credentials / secrets in repo or PR text

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- [#149](https://github.com/carloshugoeg/koicloud/pull/149) / W1-40 Preview API
- Ship review on [#155](https://github.com/carloshugoeg/koicloud/pull/155#issuecomment-6478158866)
