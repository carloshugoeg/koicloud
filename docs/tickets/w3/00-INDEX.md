# W3 — Cuentas y dinero · Jousé

Plan de tickets del workstream. Todos los tickets de este workstream ya existen como archivos
`W3-nn-<slug>.md` con `estado: abierto` y las seis secciones. `00-INDEX.md` no es un ticket y
el agente lo ignora.

| ID | Título | Rama | Estado |
|---|---|---|---|
| W3-01 | `POST /auth/register` y `POST /auth/verify` | `w3-registro-verificacion` | hecho |
| W3-02 | `POST /auth/login`, `/refresh`, `/logout` | `w3-login-sesion` | hecho ([PR #21](https://github.com/carloshugoeg/koicloud/pull/21)) |
| W3-03 | `POST /auth/forgot` y `/auth/reset` | `w3-recuperar-password` | hecho |
| W3-04 | `GET /me` y `PATCH /me` | `w3-perfil` | hecho |
| W3-05 | Módulo `notifications`: 4 plantillas y proveedor de consola | `w3-correos` | abierto |
| W3-06 | `GET /plans` y valores de la semilla | `w3-planes` | hecho |
| W3-07 | `POST /subscriptions` y `/cancel` (cableado) | `w3-contratacion` | en_revision |
| W3-08 | `GET /subscriptions` y `GET /invoices` | `w3-historiales` | hecho ([PR #55](https://github.com/carloshugoeg/koicloud/pull/55)) |
| W3-09 | Factura PDF con `fpdf2` e IVA desglosado | `w3-factura-pdf` | hecho ([PR #49](https://github.com/carloshugoeg/koicloud/pull/49)) |
| W3-10 | `GET /invoices/{id}` y `/pdf` | `w3-facturas-detalle` | en_revision |
| W3-11 | Admin: usuarios, suspender y reactivar | `w3-admin-usuarios` | abierto |
| W3-12 | Admin: ponds del sistema y bitácora | `w3-admin-ponds-bitacora` | abierto |

**El router transporta; el comando calcula.** W1-15 ya persistió `users` y `email_tokens`.
W3-01 depende de eso y **llama** `register_user` / `verify_email` / `issue_email_token`.
Importar `app.commands` no es tocar `commands/`. Si falta un campo en OpenAPI, se abre
**CCR**; si el comando ya existe, no.

**Rutas propias:** `apps/api/app/modules/{auth,users,billing,notifications,admin}/**`.
Nada de `core/`, `commands/`, `alembic/`, `packages/contracts/` ni los módulos de W1 o W4.
