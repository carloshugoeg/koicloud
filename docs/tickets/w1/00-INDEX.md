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
| W1-12 | MCP: montaje, gate, prompt, tools mutantes y confirmaciones | `w1-mcp-gate-confirm` | hecho ([PR #27](https://github.com/carloshugoeg/koicloud/pull/27); follow-ups en ticket) |
| W1-13 | Infra: Caddy, compose de producción, systemd, `deploy.yml` | `w1-infra-deploy` | abierto (requires real host — do not invent VPS) |
| W1-14 | Guion de la demo y sus tres ensayos | `w1-guion-demo` | hecho (formaliza `scripts/demo-vivo.sh` + runbook ya en `main`) |

W1 es el único workstream que puede tocar cualquier ruta, y el único que escribe migraciones,
regenera contratos (`make contracts`) y edita el harness de agentes.
