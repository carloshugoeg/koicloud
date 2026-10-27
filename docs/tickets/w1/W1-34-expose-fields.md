---
id: W1-34
workstream: W1
persona: Carlos
estado: hecho
rama: w1-expose-fields
epica: "E3-03, E8-02, E9-01"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/136"
depends_on:
---

# [W1-34] Expose size_bytes / admin totals / invoice link + MCP·CLI parity (A1)

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96) amendment A1 / A10 (API lane).
Does **not** claim W1-27 (owned by plans-pricing #123). Retention constant stays on #124.

## Qué se ve

- `PondOut.size_bytes` from the latest `pond_samples` row (null if none).
- `AdminPondOut` includes `size_bytes` and `last_error` (from `pond_status`).
- `GET /admin/totals` returns global `{users, ponds, ponds_running}` (not per-page).
- `SubscriptionOut.invoice_id` is the latest invoice for that subscription (null if none).
- MCP `get_usage` is listed and callable; the test that asserted absence is updated.
- CLI `koicloud invoice list` calls `GET /invoices`. `koicloud usage` already exists (unchanged).

Out of scope here: `pond_not_running` (needs CCR for error catalog), `PlanOut.backup_retention_days` (#124), catalog hourly pricing (#123), any `apps/web` UI.

## Entradas ya decididas (no se cambian)

- Amendment A1: expose existing columns, no migration; admin totals via a count endpoint.
- Amendment A10: MCP `get_usage`; CLI `usage` + `invoice list`.
- `GET /usage`, `GET /invoices`, `list_invoices`, `get_usage` commands already exist.
- CCR for additive OpenAPI: issue #96 comment A1 (low), same channel as #123/#124.
- Branch: `w1-expose-fields`. Ticket id: `W1-34` (W1-27..W1-33 taken by open PRs including #130 lifecycle).

## Criterios de aceptación

1. `GET /ponds` and `GET /ponds/{id}` include `size_bytes` from the latest sample (or null).
2. `GET /admin/ponds` includes `size_bytes` and `last_error`.
3. `GET /admin/totals` (admin-only) returns global user/pond/running counts; non-admin → 403.
4. `GET /subscriptions` items include `invoice_id` (latest invoice or null).
5. MCP info lists `get_usage`; tool returns the same shape as `GET /usage`; tests updated.
6. CLI `invoice list` hits `GET /invoices` with MockTransport coverage; `usage` still works.
7. No migration; no edits to #123/#124 surfaces (`plan_pricing` / `plan_retention`); no `apps/web` UI files (generated `schema.d.ts` via `make contracts` only).
8. `make check-api` and `make check-cli` green (or documented Postgres gap with unit coverage).

## No tocar

- `apps/web/src/**` except generated `schema.d.ts` from `make contracts`.
- Ticket ids W1-27..W1-32 and open PR branches that claim them (`w1-plans-pricing`, `w1-backup-retention`, `w1-pond-stop-start`, `w1-admin-suspend-reason`, `w1-nit-checkout-invoice`, `w1-admin-subscriptions`).
- `PlanOut.backup_retention_days` / `plan_retention.py` (owned by #124 / W1-28).
- Error catalog / `pond_not_running` (CCR required).
- Alembic migrations; PlanOut pricing/retention fields.

## Si algo falta

`BLOQUEADO: requiere CCR porque …` only if a frozen surface beyond A1 amendment must change.
Do not invent approval for `pond_not_running`.

## Referencia

PR [#82](https://github.com/carloshugoeg/koicloud/pull/82) (admin ponds) · [#84](https://github.com/carloshugoeg/koicloud/pull/84) (CLI resto) · [#86](https://github.com/carloshugoeg/koicloud/pull/86) (MCP read tools) · amendment [comment](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428918452).
