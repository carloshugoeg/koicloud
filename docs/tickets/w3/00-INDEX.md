# W3 — Cuentas y dinero · Jousé

Plan de tickets del workstream. Un ticket se trabaja **solo** cuando existe su archivo
`W3-nn-<slug>.md` con `estado: abierto` y las seis secciones. Mientras diga *por escribir*,
no existe todavía. `00-INDEX.md` no es un ticket y el agente lo ignora.

| ID | Título | Rama | Estado |
|---|---|---|---|
| W3-01 | `POST /auth/register` y `POST /auth/verify` | `w3-registro-verificacion` | por escribir |
| W3-02 | `POST /auth/login`, `/refresh`, `/logout` | `w3-login-sesion` | por escribir |
| W3-03 | `POST /auth/forgot` y `/auth/reset` | `w3-recuperar-password` | por escribir |
| W3-04 | `GET /me` y `PATCH /me` | `w3-perfil` | por escribir |
| W3-05 | Módulo `notifications`: 4 plantillas y proveedor de consola | `w3-correos` | por escribir |
| W3-06 | `GET /plans` y valores de la semilla | `w3-planes` | por escribir |
| W3-07 | `POST /subscriptions` y `/cancel` (cableado) | `w3-contratacion` | por escribir |
| W3-08 | `GET /subscriptions` y `GET /invoices` | `w3-historiales` | por escribir |
| W3-09 | Factura PDF con `fpdf2` e IVA desglosado | `w3-factura-pdf` | por escribir |
| W3-10 | `GET /invoices/{id}` y `/pdf` | `w3-facturas-detalle` | por escribir |
| W3-11 | Admin: usuarios, suspender y reactivar | `w3-admin-usuarios` | por escribir |
| W3-12 | Admin: ponds del sistema y bitácora | `w3-admin-ponds-bitacora` | por escribir |

**El router transporta; el comando calcula.** Los invariantes de dinero (cómo se calcula la
factura, el IVA, el prorrateo, la renovación y la cuota por plan) y los primitivos de token
y hash ya están escritos en `app/commands/` y `app/core/`, y son de W1. Si tu endpoint
necesita un campo que no existe, se abre **CCR**; no se agrega.

**Rutas propias:** `apps/api/app/modules/{auth,users,billing,notifications,admin}/**`.
Nada de `core/`, `commands/`, `alembic/`, `packages/contracts/` ni los módulos de W1 o W4.
