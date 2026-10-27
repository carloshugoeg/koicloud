# Pond stop / start statechart (CCR #131)

Agreed public stop/start flow. TLC-checked before product code.

Five UI phases only: running, stopping, stopped, starting, error.
No pending / En cola / provisioning in this chart.

| File | Role |
|------|------|
| `pond-stop-start.mmd` | Hand chart |
| `PondStopStart.tla` + `.cfg` + `.map.mjs` | TLC model + reader labels |
| `chart.mmd` / `report.md` / `tlc.out` / `summary.json` | Last TLC run |

Readable diagram for reviewers:

- Mermaid: `docs/architecture/diagrams/21-pond-stop-start.mmd`
- PNG: `docs/architecture/diagrams/21-pond-stop-start.png`
- SVG: `docs/architecture/diagrams/21-pond-stop-start.svg`

## Happy / error transitions

```mermaid
stateDiagram-v2
  [*] --> running
  running --> stopping: POST /stop
  stopping --> stopped: job stop ok
  stopped --> starting: POST /start
  starting --> running: job start ok
  stopping --> error: job stop failed
  starting --> error: job start failed
  error --> stopping: POST /retry [stop_pond]
  error --> starting: POST /retry [start_pond|create_pond]
```

Recovery from `error` is **only** `POST /retry`. The API sets observed so the
UI shows **Deteniendo…** (stop) or **Iniciando…** (start/create), never En cola.
`POST /start` from `observed=failed` stays `409 pond_busy`.

`stopping` / `starting` are **UI phases** (`desired ≠ observed` + job in flight).
The observed enum does not gain new values.

## 409 `pond_busy` (no phase change)

| Current phase | Request | Why |
|---|---|---|
| `stopped` | `POST /stop` | stop needs `observed=running` |
| `running` | `POST /start` | start needs `observed=stopped` |
| `error` (`observed=failed`) | `POST /start` or `/stop` | use `/retry` |
| `stopping` | `POST /stop` or `/start` | job already in flight |
| `starting` | `POST /stop` or `/start` | job already in flight |
| any with active `queued\|running` job | either | `jobs_one_active` / double-click |

Also: `404 pond_not_found`, `403 not_owner`, `503 node_unavailable`.
SQL on a non-running pond keeps `409 pond_not_running` (r2 A4).

## Regenerate

```bash
export PATH="$HOME/.local/bin:$PATH"
export TLA2TOOLS=/path/to/tla2tools.jar
export JAVA=java
node <statechart-skill>/scripts/statechart PondStopStart.tla \
  --view PondStopStart.map.mjs --out /tmp/pond-stop-start-out
```

Invariant that must stay green: `TypeOK` (5 chart phases; 0 rule breaks).
