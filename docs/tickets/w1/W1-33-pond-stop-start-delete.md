---
id: W1-33
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-pond-stop-start
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/130"
depends_on: W1-17 W1-10
---

# [W1-33] Pond lifecycle statechart (stop / start / delete with backup)

Renumbered from draft W1-27 (that ID belongs to [#123](https://github.com/carloshugoeg/koicloud/pull/123) plans-pricing).

## Qué se ve

**This PR (criterion 1 only):** the agreed pond lifecycle diagram is in the repo and in
PR #130, TLC-checked, before any product code.

- Mermaid + PNG: `docs/architecture/diagrams/20-pond-lifecycle-stop-start-delete.*`
- Spec: `docs/architecture/statecharts/pond-lifecycle/` (`PondLifecycle.tla` + cfg + map)
- Invariants green: `GoneWhileWantedOn`, `GoneWhileWantedOff`,
  `OnlineAfterYouRemovedIt`, `OfflineAfterYouRemovedIt`, `GoneOnlyWhenRemoved`

**Follow-up PR (after CCR [#131](https://github.com/carloshugoeg/koicloud/issues/131) is
approved):** user-facing stop/start and any contract edits. Until then, freeze holds:

- no `POST /ponds/{id}/stop` or `/start`
- no new signatures in `commands/ponds.py`
- no edits to `api-surface.md` or `data-model.md` §4.1

Delete-with-`pre_delete` already lives on `main`; this ticket does not re-implement it.

## Entradas ya decididas (no se cambian)

- Enums already on `main`: `PondDesiredState.stopped`, `JobType.start_pond|stop_pond`,
  `BackupKind.pre_delete`. Node-agent handlers for start/stop already exist.
- `jobs_one_active` and the live delete → pre_delete → `delete_pond` chain stay as today.
- **CCR [#131](https://github.com/carloshugoeg/koicloud/issues/131)** must be approved
  before OpenAPI routes, command signatures, or `api-surface` / `data-model` §4.1 change.
- Survey (open PRs): W1-27=#123, W1-28=#124, W1-30=#121, W1-31=#133, W1-32=#132 → this
  ticket is **W1-33**.

## Criterios de aceptación

1. Diagrama `20-pond-lifecycle-stop-start-delete` + PNG + spec TLC in PR #130; summary
   invariants green. **In scope for this PR.**
2. *(Follow-up, needs CCR #131)* `POST .../stop` → 202, `desired=stopped`, job
   `stop_pond`; complete → `observed=stopped`.
3. *(Follow-up, needs CCR #131)* `POST .../start` → 202, `desired=running`, job
   `start_pond`; complete → `observed=running`.
4. *(Follow-up)* Wrong observed / active job → catalog errors (`pond_busy` /
   `pond_not_found`).
5. *(Already on main; not re-done here)* `DELETE` enqueues `pre_delete` first.
6. *(Follow-up)* CLI/MCP stop/start without confirm → `409 confirmation_required`.
7. *(Follow-up)* `make check-api` and `make check-node-agent` for the impl PR.
8. One ticket file (`W1-33`). No frozen-contract edits without approved CCR.

## No tocar

Frozen until CCR #131 approved: `apps/api/app/commands/ponds.py`,
`docs/architecture/api-surface.md`, `docs/architecture/data-model.md` §4.1,
`packages/contracts/openapi.json`, `apps/web/src/api/schema.d.ts`, Alembic.
Do not invent error codes. Do not merge this PR without Carlos’s yes (high-risk).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

`docs/architecture/diagrams/20-pond-lifecycle-stop-start-delete.mmd`,
`docs/architecture/statecharts/pond-lifecycle/`, CCR #131, W1-17, W1-10,
[how notes](https://github.com/carloshugoeg/koicloud/pull/130) from Wave B1 explorers.
