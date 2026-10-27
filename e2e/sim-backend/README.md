# Simulated control plane

This process is an in-memory stand-in for preview checks. It is not the production API. `POST /api/v1/ponds/{id}/stop` and `POST /api/v1/ponds/{id}/start` exist only here. They are not in OpenAPI.

Create ends in `running`. The sim applies start in the same request because it has no worker.

`DELETE /api/v1/ponds/{id}` returns `409` with `confirmation_required`. `POST /api/v1/confirm/{token}` runs the delete. MCP mutators use the same two steps. Read SQL does not.

Read stubs match OpenAPI shapes: `GET /api/v1/ponds/{id}/sql/history` and `GET /api/v1/admin/ponds`. MCP errors use only api-surface §7 / `lib/errors.ts` codes: unknown tool or missing args → `internal_error`, bad restore id → `pond_not_found`, MCP auth failure → `agent_bad_credentials`.

## Start the sim

Run this from the repo root.

```bash
python e2e/sim-backend/__main__.py
```

The process listens on `127.0.0.1` port `18080`. Set `KOI_SIM_PORT` to use another port.

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health
```

## Seed the gate users

Set the sim URL and an absolute file path. The script writes passwords only to that file.

```bash
export KOI_SIM_BASE_URL=http://127.0.0.1:18080
export KOI_GATE_CREDENTIALS_OUT=/absolute/path/credentials.json
bash scripts/seed-gate-preview.sh
```

Stdout prints `seeded`, `gate-admin@koicloud.test`, `gate-user@koicloud.test`, and the file path.

The script allows `localhost`, `127.0.0.1`, and host names that end in `.test`. With `KOI_ALLOW_PREVIEW_SEED=1` it also allows non-production `*.vercel.app` hosts (the preview-hosted sim). It always refuses `koicloud.dev`, `koicloud.com`, and production Vercel aliases.

## Preview-hosted sim (Vercel)

Preview deployments of `apps/web` host the real `apps/api` (SimulatedPaymentProvider + preview DB) behind `/api/v1/*` and `/mcp`. This local `e2e/sim-backend` toy remains for offline/dev only — it is not mounted on Vercel.

```bash
export KOI_SIM_BASE_URL=https://<preview>.vercel.app
export KOI_ALLOW_PREVIEW_SEED=1
export KOI_GATE_CREDENTIALS_OUT=/absolute/path/credentials.json
bash scripts/seed-gate-preview.sh
curl -fsS "$KOI_SIM_BASE_URL/api/v1/health"
```

A second run with the same credentials file logs in again and keeps a still-valid MCP password. Restart the process (or a cold Vercel instance) to drop memory.

Ctrl-C stops the local process.
