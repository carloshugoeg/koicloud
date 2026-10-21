# k6 load scenarios (W4-08)

Three demo-path scenarios against a configured API origin:

| Script | Route | Success |
|--------|-------|---------|
| `scenarios/login.js` | `POST /api/v1/auth/login` | 200 + `access_token` |
| `scenarios/list_ponds.js` | `GET /api/v1/ponds` | 200 |
| `scenarios/create_pond.js` | `POST /api/v1/ponds` | 202 or 409 (propose only) |

## Thresholds (RNF-01)

- 20 VUs for 30 s
- `http_req_duration` p95 `< 500` ms
- `http_req_failed` rate `< 1%`

Do not relax thresholds if they fail. Capture the summary and record the failure in `docs/reporte-carga.md`.

## Environment

| Variable | Required | Default |
|----------|----------|---------|
| `BASE_URL` | yes | — (e.g. `http://127.0.0.1:8000`) |
| `KOI_EMAIL` | no | `demo@koicloud.dev` |
| `KOI_PASSWORD` | no | seed password from README |

## Run

```bash
# one scenario
BASE_URL=http://127.0.0.1:8000 k6 run load/k6/scenarios/login.js

# all three + JSON under load/k6/results/<stamp>-<commit>/
BASE_URL=http://127.0.0.1:8000 bash load/k6/run-all.sh
```

VPS demo URL and secrets are owned by W1 (ticket W1-13). Agents do not deploy.
