---
id: W1-33
workstream: W1
persona: Carlos
estado: hecho
rama: w1-pond-stop-start
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/130"
depends_on: W1-17 W1-10
---

# [W1-33] Pond stop/start (CCR #131)

Renumbered from draft W1-27 (that ID belongs to [#123](https://github.com/carloshugoeg/koicloud/pull/123) plans-pricing).

## Qué se ve

Approved CCR [#131](https://github.com/carloshugoeg/koicloud/issues/131). Statechart first, then public stop/start.

- Diagram: `docs/architecture/diagrams/21-pond-stop-start.*` + TLC under `docs/architecture/statecharts/pond-stop-start/`
- Keep **Detener**; add **Iniciar** on pond detail
- `POST /api/v1/ponds/{id}/stop` → `stop_pond`; `POST .../start` → `start_pond`; `202 {pond, job}`
- CLI/MCP without token → `confirmation_required`
- 404 `pond_not_found` | 403 `not_owner` | 409 `pond_busy` | 503 `node_unavailable`
- No migration. Do not touch PlanOut / #123.

## Entradas ya decididas (no se cambian)

- Enums already on `main`: `PondDesiredState.stopped`, `JobType.start_pond|stop_pond`.
- Node-agent handlers for start/stop already exist.
- Wrong state reuses `pond_busy` (no new error code).
- `stopping`/`starting` are UI phases (`desired≠observed` + job); no observed-enum change.
- SQL on non-running keeps `409 pond_not_running`.

## Criterios de aceptación

1. Statechart (running/stopping/stopped/starting/error/provisioning) + every 409 case documented; in PR body.
2. `POST .../stop` → 202, `desired=stopped`, job `stop_pond`; complete → `observed=stopped`.
3. `POST .../start` → 202, `desired=running`, job `start_pond`; complete → `observed=running`.
4. Wrong observed / active job → `pond_busy` 409; unknown → 404; other owner → 403.
5. CLI/MCP stop/start without confirm → `409 confirmation_required`.
6. Web: Detener running→stopping→stopped; Iniciar→starting→running; buttons disabled in flight.
7. API tests 202/404/403/409 + transition coverage; `make check-api` / `check-web` / `check-cli`.
8. No PlanOut / #123 edits. No migration.

## No tocar

`PlanOut` / PR #123 pricing fields. Alembic. Do not merge without Carlos’s yes (high-risk). W1-34 ticket status is owned by PR #147 — do not mark it aquí.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

CCR #131 comment, `docs/architecture/diagrams/21-pond-stop-start.mmd`,
`docs/architecture/statecharts/pond-stop-start/`, W1-17, W1-10.
