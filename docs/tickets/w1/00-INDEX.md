# W1 — Núcleo y data plane · Carlos

Plan de tickets del workstream. Un ticket se trabaja **solo** cuando existe su archivo
`W1-nn-<slug>.md` con `estado: abierto` y las seis secciones. Mientras diga *por escribir*,
no existe todavía. `00-INDEX.md` no es un ticket y el agente lo ignora.

| ID | Título | Rama | Estado |
|---|---|---|---|
| W1-01 | Scaffold del repo + harness de agentes (Fase 0) | `w1-scaffold` | cerrado (en `main`, sin archivo de ticket) |
| W1-02 | Migraciones `0001_initial` y `0002_seed_plans` | `w1-migraciones-iniciales` | cerrado (en `main`, sin archivo de ticket) |
| W1-03 | `core/`: config, errores, seguridad, cripto, db, deps de auth | `w1-core` | cerrado (en `main`, sin archivo de ticket) |
| W1-04 | `commands/`: todas las firmas del catálogo | `w1-command-signatures` | cerrado (en `main`, sin archivo de ticket) |
| W1-05 | Routers registrados con `example` → OpenAPI v0 congelado | `w1-openapi-freeze` | cerrado (en `main`, sin archivo de ticket) |
| W1-06 | Andamio de `apps/web`: cliente, auth-store, tema, MSW | `w1-web-scaffold` | cerrado (en `main`, sin archivo de ticket) |
| W1-07 | Andamio de `apps/cli`: cliente, config, comando de referencia | `w1-cli-scaffold` | cerrado (en `main`, sin archivo de ticket) |
| W1-08 | Node-agent con `mock_driver` y cola de jobs | `w1-node-agent-mock` | cerrado (en `main`, sin archivo de ticket) |
| W1-09 | `create_pond` persistido + job claim (+ delete/retry) | `w1-persist-create-pond` | hecho ([PR #6](https://github.com/carloshugoeg/koicloud/pull/6); delete/retry en #17/#18) |
| W1-15 | `users` + `email_tokens` persistidos | `w1-auth-persist` | hecho ([PR #7](https://github.com/carloshugoeg/koicloud/pull/7)) |
| W1-16 | MSW fixtures + ticket/docs honesty + `list_plans` | `w1-teammate-unblock-semana` | hecho ([PR #19](https://github.com/carloshugoeg/koicloud/pull/19)) |
| W1-10 | Respaldos diarios y restauración verificada | `w1-backups` | hecho ([PR #30](https://github.com/carloshugoeg/koicloud/pull/30)) |
| W1-11 | Muestreo y agregación de consumo | `w1-metering` | hecho ([PR #36](https://github.com/carloshugoeg/koicloud/pull/36)) |
| W1-12 | MCP: montaje, gate, prompt, tools mutantes y confirmaciones | `w1-mcp-gate-confirm` | hecho ([PR #27](https://github.com/carloshugoeg/koicloud/pull/27); follow-ups [#38](https://github.com/carloshugoeg/koicloud/pull/38)) |
| W1-13 | Infra: Caddy, compose de producción, systemd, `deploy.yml` | `w1-infra-deploy` | abierto · groundwork [#39](https://github.com/carloshugoeg/koicloud/pull/39) · ESPERA host real |
| W1-14 | Guion de la demo y sus tres ensayos | `w1-guion-demo` | hecho (formaliza `scripts/demo-vivo.sh` + runbook ya en `main`) |
| W1-18 | Demo vivo S3 (subscribe → usage → PDF+IVA → backup → restore) | `w1-demo-vivo-s3` | hecho ([PR #75](https://github.com/carloshugoeg/koicloud/pull/75)) |
| G4 | Wire `get_invoice_pdf` to the W3-09 renderer | `w1-g4-invoice-pdf-wire` | en_revision |
| G1 | Persist invoices, payments, and subscribe | `w1-g1-billing-persistence` | hecho ([PR #54](https://github.com/carloshugoeg/koicloud/pull/54)) |
| G2 | Daily renewal via `BillingService.renew` (E2-04) | `w1-g2-daily-renewal` | en-revision |
| W1-17 | Reconciler mínimo (G3 / E4-05) | `w1-g3-reconciler` | en-revision ([PR #53](https://github.com/carloshugoeg/koicloud/pull/53)) |

W1 es el único workstream que puede tocar cualquier ruta, y el único que escribe migraciones,
regenera contratos (`make contracts`) y edita el harness de agentes.
