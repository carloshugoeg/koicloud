---
id: W1-38
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-e2e-preview-verify
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/142"
depends_on:
---

# [W1-38] Preview e2e: ponds + MCP client + Playwright CI

Renumbered from draft W1-37 after W1-36 was claimed by Wave C0 #140. Companion seed
ticket is W1-37.

## Qué se ve

One verification PR (never merged) runs Playwright in CI against a Vercel **preview**
plus the simulated backend from W1-37. Pass/fail table covers every pond step
(create, start, stop, backup, delete, limits/errors) and every MCP tool from a real
MCP JSON-RPC client. Screenshots or short clips at 375 and 1440 land in the Project
store under `media/e2e-verify/`. Failures each get their own follow-up fix PR.

## Entradas ya decididas (no se cambian)

- Preview only. Test data only. Never prod.
- Simulated backend until VPS (`e2e/sim-backend/`).
- Real MCP client suite covers tools listed in `app/mcp/router.py`
  (`READ_ONLY_TOOLS` + `MUTABLE_TOOLS`), plus auth failure and reconnect.
- Secrets never appear in PR/commit/log/comment/summary. Gate credentials only via
  store `media/gate-access/credentials.json` (agent-written, not committed).
- Do not edit files owned by other open PR tickets.
- Never merge. No push to `main`. Frozen contracts need CCR.
- Ticket IDs: W1-37 (seed) + W1-38 (this). W1-36 is Wave C0 #140 only.

## Criterios de aceptación

1. `.github/workflows/e2e-preview.yml` runs on the PR and executes Playwright + MCP suite.
2. Pass/fail table at store `docs/e2e-verify-results.md` with one row per flow and per tool.
3. Media at store `media/e2e-verify/` for each flow at 375 and 1440.
4. Pond flows: create, start (running), stop (sim), backup, delete, limits/errors.
5. MCP: every tool invoked via real client against sim `/mcp`.
6. Each FAIL filed as its own ticket-scoped fix PR (separate from this one).

## No tocar

Same fences as W1-37. Do not modify `#140` compose e2e workflow. Do not merge.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

W1-37, `scripts/demo-mcp-replay.py`, polish-finish plan Phase 3, Vercel preview env
`VITE_ENABLE_MOCKS` (note: production builds still require `DEV` for MSW today).
