---
id: W1-37
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-e2e-preview-verify
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/142"
depends_on:
---

# [W1-37] Gate preview seed + simulated backend (test data only)

Renumbered from draft W1-36 (that ID belongs to Wave C0 [#140](https://github.com/carloshugoeg/koicloud/pull/140)).

## Qué se ve

Idempotent seed for preview/sim gate users and one narrow MCP credential for the test
user. Simulated control-plane HTTP + MCP under `e2e/sim-backend/` until VPS exists.
Credentials land only in the Project store path named by `KOI_GATE_CREDENTIALS_OUT`
(never in git, CI logs, or PR bodies).

## Entradas ya decididas (no se cambian)

- Emails: `gate-admin@koicloud.test`, `gate-user@koicloud.test` (fake data only).
- Seed refuses production hosts/URLs (localhost / `*.test` / explicit allow only).
- MCP gate stays slug + password Basic auth (existing contract). No OpenAPI edits.
- Sim-only `POST /ponds/{id}/stop` and `/start` live in the sim server only. Real
  stop/start HTTP stays frozen until CCR #131.
- Do not edit `apps/web/src/main.tsx` or `apps/web/src/mocks/*` (owned by open PRs).
- Do not edit `#140` files under `e2e/{docker-compose,lib,logging,run,suite}*`.
- Do not claim `W1-36` (Wave C0 compose e2e on #140).

## Criterios de aceptación

1. `bash scripts/seed-gate-preview.sh` is idempotent against `KOI_SIM_BASE_URL`.
2. Script exits non-zero on production-like URLs without printing secrets.
3. Sim backend serves health, auth, plans/subscribe, ponds (create→running), backup,
   SQL, delete propose→confirm, admin suspend, agent-access, and MCP JSON-RPC tools.
4. When `KOI_GATE_CREDENTIALS_OUT` is set, secrets are written only there; stdout has
   no password or token values.
5. Ticket + INDEX row exist. No frozen-contract edits.

## No tocar

`packages/contracts/**`, `apps/api/app/commands/**` signatures, Alembic, OpenAPI,
`apps/web/src/main.tsx`, `apps/web/src/mocks/**`, `#140` e2e compose files, `main` push,
any merge.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints en el API real; el sim puede espejar CCR #131 solo en proceso.

## Referencia

`scripts/seed-dev.sh`, `scripts/demo-mcp-replay.py`, CCR #131, W1-33, Wave C0 #140 (W1-36).
