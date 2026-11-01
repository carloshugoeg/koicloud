---
name: koicloud-formal-verification
description: KoiCloud system map and formal checks (L0/L1/L2 statecharts + TLA+). Use to locate a bug from a symptom, or to check changes to auth/session, agent access, admin suspend, metering/billing, workers, against the TLA+ model in docs/statechart/model. Use when a change touches pond lifecycle endpoints or jobs (stop/start/retry/backup/restore/delete), the SQL console, pond detail tabs, session/auth persistence, the sidebar nav, or checkout.
---

# KoiCloud formal verification (system map)

System map: `docs/statechart/system.md` (L0 context, L1 subsystems + flows F1-F9), `docs/statechart/level2/*.md` (one per subsystem), `docs/statechart/ponds.md` (pond lifecycle + web journey).

Three TLA+ models (`System`, `PondLifecycle`, `UserJourney`), checked with TLC. Statecharts and the transition table are in `docs/statechart/ponds.md`; the contract is issue #96 (r2 A5, r3 stop/start, r6 UI/nav).

## Does my change touch the verified code?

| Model / rule | Covered code |
|---|---|
| `PondLifecycle`: OneInFlightOp, NoStartOnDeleted, ConsoleOnlyWhenRunning | `apps/api/app/modules/ponds/service.py` (`_assert_no_active_job`, `stop`, `start`, `delete`, `retry_failed`, `get_owned`), `apps/api/app/modules/backups/service.py` (`restore`, backups), `apps/api/app/modules/sql_console/*`, `apps/node-agent/agent/handlers/*_pond.py`, `apps/web/src/features/ponds/pond-lifecycle-actions.tsx`, `pond-state.ts` |
| `UserJourney`: TabsFixedOrder | `apps/web/src/features/ponds/detail-page.tsx`, `backups-page.tsx`, `apps/web/src/features/sql-console/sql-console-page.tsx` |
| HistoryScoped | `apps/api/app/modules/sql_console/service.py` (`list_for_actor`), `apps/web/src/api/hooks/sql-console.ts`, `apps/web/src/mocks/handlers.ts` (sql/history) |
| ReloadKeepsSession | `apps/web/src/lib/auth-store.ts` (access token in memory), `apps/web/src/app/session-boot-gate.tsx` (boot calls `/auth/refresh`), `apps/web/src/api/client.ts`, cookie `koi_refresh` |
| PlansViaBilling | `apps/web/src/app/layout/nav-config.ts`, `apps/web/src/app/router.tsx`, `apps/web/src/features/uso/*`, `features/plans/plans-page.tsx` |
| NoChargeBadCard | `apps/web/src/features/plans/checkout-modal.tsx`, `apps/api/app/modules/billing/service.py` |

Last confirmed in sync with code at commit **72015b5** (main, 2026-10-30). Run `git diff 72015b5 -- <files above>`; any hit means re-read the model. Move this commit forward only after you confirm the model still describes the code at the new commit.

| `System`: NoPondApiWhenLoggedOut, NoPondApiWhenSuspended, AgentScopeWithinOwner, DeletedPondHasNoJobs, DeletedPondAccruesNoUsage | `apps/api/app/core/auth.py` (`get_current_user`), `core/security.py`, `core/config.py` (`access_token_ttl_minutes`), `commands/auth.py`, `commands/admin.py` (`suspend_user`), `modules/agent_access/service.py` (`authenticate`), `mcp/server.py`, `modules/metering/service.py` (`compute_day_metrics`, `aggregate_day`), `workers/reconciler.py`, `modules/jobs/service.py` |

## Bug hunt map (symptom → where to look)

| Symptom | Level / doc | Model rule | First code to open |
|---|---|---|---|
| Logged out on reload / random logouts | L2 auth-session (A6-A8) | ReloadKeepsSession | `apps/web/src/lib/auth-store.ts`, `app/session-boot-gate.tsx`, `api/client.ts` |
| API works after logout or suspend | L1 F1/F7, L2 auth-session, admin | NoPondApiWhenLoggedOut / Suspended | `core/auth.py:get_current_user`, `commands/admin.py:suspend_user` |
| Agent does something the owner can't | L1 F6, L2 agent-access (G7) | AgentScopeWithinOwner | `modules/agent_access/service.py:authenticate`, `mcp/server.py` |
| Pond stuck in Provisioning / Stopping / Deleting | L2 provisioning-workers, ponds.md | OneInFlightOp | `modules/jobs/service.py`, `workers/reconciler.py`, node-agent `handlers/` |
| 409 pond_busy unexpectedly | ponds.md L19 | OneInFlightOp | `ponds/service.py:_assert_no_active_job` |
| Deleted pond comes back / accepts actions | ponds.md L20, workers W6 | NoStartOnDeleted | `ponds/service.py:get_owned`, `reconciler.py` REMEDIATE |
| Charged for a deleted or stopped pond | L1 F5, L2 billing M7 | DeletedPondAccruesNoUsage | `metering/service.py:compute_day_metrics` |
| Checkout does nothing / wrong total | L2 billing M1-M3, ponds.md J11-J17 | NoChargeBadCard | `features/plans/checkout-modal.tsx`, `billing/service.py` |
| Wrong price somewhere | L2 billing M8 | — (tests) | `billing/plan_pricing.py`, web `formatPrice` |
| Tabs missing / reordered | ponds.md J5-J8 | TabsFixedOrder | `features/ponds/detail-page.tsx`, `backups-page.tsx`, `sql-console/sql-console-page.tsx` |
| Console shows other ponds' queries | L2 sql-console S4 | HistoryScoped | `sql_console/service.py:list_for_actor`, `mocks/handlers.ts` |
| Backup missing / not restorable | L2 backups | — | `backups/service.py`, node-agent `backup_pond.py` |
| Email not received | L0 Resend, L1 F8 | — (not modelled) | `modules/notifications/` (`email_mode.py`, `resend.py`) |

Start at L0 to decide which external entity is involved, L1 to pick the subsystem and flow, then the L2 file's transition row; its e2e test name is the repro to write.

## Run

```sh
docs/statechart/model/check.sh      # needs Java 11+; downloads tla2tools.jar v1.8.0 if TLA2TOOLS is unset and ./tla2tools.jar is missing
```

Expected today: `PASS` for `PondLifecycle.cfg`, `UserJourneyFixed.cfg`, `SystemFixed.cfg`; journey AS-IS shows 4 `BREAKS` (r6 findings still open) and `holds ReloadKeepsSession`; system AS-IS shows 4 `BREAKS` and `holds DeletedPondHasNoJobs`. Runs in a few seconds. Exit code is non-zero only if a target model fails.

- `UserJourneyFixed.cfg` (`Fixed = TRUE`) is the target behaviour. `UserJourneyAsIs.cfg` (`Fixed = FALSE`) is what main does today. When an r6 item ships, change the matching `IF Fixed` branch in `UserJourney.tla` so the as-is branch matches the code, and the AS-IS line should flip to `holds`. When all hold, delete the `Fixed` constant.

## Read results

Read every result, and redraw the charts, with the pstack `/statechart` skill (views: `docs/statechart/model/lifecycle.view.ts`, `journey.view.ts`, `system.view.ts`). It prints each violated rule's shortest path in plain words.

Real bug vs modelling error: replay the path step by step in the code (API test in `apps/api/tests/test_pond_stop_start.py` style, or Playwright in `e2e/pond-lifecycle/`). If the code does not do what the path says, the model is wrong: fix the model and cite the code line. Never weaken an invariant to get a pass.

## Proof it can fail

In `System.tla`, leaving `jobs' = 1` in `DeleteEnds` makes TLC report `DeletedPondHasNoJobs`. Removing the `jobs = 0` guard in `Accept` (mirrors deleting `_assert_no_active_job`) makes TLC report `OneInFlightOp` and `TypeOK` violated. Setting `Fixed = FALSE` reproduces the five journey findings Carlos saw manually.

## Scope

Bounded: one pond for the lifecycle, two ponds (one brand-new) for the console history, one user. Not modelled: concurrent users/nodes, scheduler and reconciler, token-expiry races, admin suspend, delete after a failed pre_delete backup, colours (Detener red).
