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
| W1-19 | Wire `admin_list_ponds` / `admin_list_audit` → AdminService | `w3-admin-ponds-bitacora` | hecho ([PR #82](https://github.com/carloshugoeg/koicloud/pull/82)) |
| W1-20 | Guardias para errores repetidos de agentes | `w1-agent-mistake-guards` | hecho ([PR #88](https://github.com/carloshugoeg/koicloud/pull/88)) |
| G4 | Wire `get_invoice_pdf` to the W3-09 renderer | `w1-g4-invoice-pdf-wire` | hecho ([PR #50](https://github.com/carloshugoeg/koicloud/pull/50)) |
| G1 | Persist invoices, payments, and subscribe | `w1-g1-billing-persistence` | hecho ([PR #54](https://github.com/carloshugoeg/koicloud/pull/54)) |
| G2 | Daily renewal via `BillingService.renew` (E2-04) | `w1-g2-daily-renewal` | hecho ([PR #74](https://github.com/carloshugoeg/koicloud/pull/74)) |
| W1-17 | Reconciler mínimo (G3 / E4-05) | `w1-g3-reconciler` | hecho ([PR #53](https://github.com/carloshugoeg/koicloud/pull/53)) |
| W1-21 | Partir `PondService` (SRP / DIP) | `w1-pond-service-srp` | abierto · desde P7 solid-review |
| W1-22 | Transiciones de job explícitas (OCP) | `w1-job-transitions-ocp` | abierto · depende W1-21 |
| W1-23 | Historial SQL vía commands (DIP) | `w1-sql-history-dip` | abierto · desde P7 solid-review |
| W1-24 | Revisión SOLID del control plane (P7 / #96) | `w1-solid-review` | hecho ([PR #101](https://github.com/carloshugoeg/koicloud/pull/101)) |
| W1-25 | ADRs A-01..A-12 en `docs/adr/` | `w1-architecture-adrs` | hecho ([PR #106](https://github.com/carloshugoeg/koicloud/pull/106)) |
| W1-26 | `scripts/demo-mcp-replay.py` (antes W4-09) | `w1-demo-replay` | hecho ([PR #110](https://github.com/carloshugoeg/koicloud/pull/110)) |
| W1-27 | Plan pricing from `GET /plans` (#96 amendment) | `w1-plans-pricing` | hecho ([PR #123](https://github.com/carloshugoeg/koicloud/pull/123)) · **money** |
| W1-28 | PlanOut.backup_retention_days constant (A3) | `w1-backup-retention` | en-revision · [#124](https://github.com/carloshugoeg/koicloud/pull/124) |
| W1-29 | *(renumbered → W1-32 on #132)* | — | ver W1-32 |
| W1-30 | Motivo de suspensión en bitácora + `user_not_found` | `w1-admin-suspend-reason` | hecho ([PR #121](https://github.com/carloshugoeg/koicloud/pull/121); CCR [#125](https://github.com/carloshugoeg/koicloud/issues/125)) |
| W1-31 | NIT checkout → invoice (#96 A2) | `w1-nit-checkout-invoice` | hecho ([PR #133](https://github.com/carloshugoeg/koicloud/pull/133)) · CCR #127 |
| W1-32 | Admin subscriptions (#96 A7) | `w1-admin-subscriptions` | bloqueado · [#132](https://github.com/carloshugoeg/koicloud/pull/132) CCR #128 |
| [W1-33](W1-33-pond-stop-start.md) | Pond stop/start (CCR #131) | `w1-pond-stop-start` | hecho · [#130](https://github.com/carloshugoeg/koicloud/pull/130) · CCR [#131](https://github.com/carloshugoeg/koicloud/issues/131) approved |
| W1-34 | Expose size_bytes / admin totals / invoice link + MCP·CLI (A1) | `w1-expose-fields` | hecho · [#136](https://github.com/carloshugoeg/koicloud/pull/136) · **no** `PlanOut.backup_retention_days` (#124/W1-28) |
| W1-35 | Columna Expira / `BackupOut.expires_at` (A11) | `w1-a11-expira-toasts` | hecho · [#134](https://github.com/carloshugoeg/koicloud/pull/134) |
| W1-36 | Wave C0: compose prod, deploy.sh SSH, e2e compose CI | `w1-wave-c0-compose-e2e` | hecho ([PR #140](https://github.com/carloshugoeg/koicloud/pull/140)) |
| W1-40 | Preview API rewrite + theme (HIGH lane; real preview API) | `w1-preview-api-theme-fix` | hecho · [#149](https://github.com/carloshugoeg/koicloud/pull/149) |
| [W1-42](W1-42-preview-login-e2e.md) | Regresión e2e del login en Preview | `w1-preview-login-gate` | hecho · [#159](https://github.com/carloshugoeg/koicloud/pull/159) |
| [W1-44](W1-44-email-resend.md) | Proveedor de correo Resend (prod) + consola default | `w1-email-resend` | en-revision · [#161](https://github.com/carloshugoeg/koicloud/pull/161) |
| [W1-45](W1-45-auth-session-persist.md) | Recargar conserva la sesión (cookie `koi_refresh`) | `w1-auth-session-persist` | en-curso · #96 r6-3 |

W1 es el único workstream que puede tocar cualquier ruta, y el único que escribe migraciones,
regenera contratos (`make contracts`) y edita el harness de agentes.
