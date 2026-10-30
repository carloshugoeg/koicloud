# KoiCloud system map (DFD-style levels)

Grounded in contract #96 (r2–r5) and `origin/main` @ `72015b5`. Level 2 files are in [`level2/`](level2/); the pond lifecycle and user journey are in [`ponds.md`](ponds.md). TLA+ models: [`model/`](model/) (re-run with `model/check.sh`).

## Level 0: context

```mermaid
flowchart LR
  U([Cliente / operador<br/>web SPA]) -- login, ponds, SQL, checkout --> K((KoiCloud))
  K -- tokens, pond state, results, invoices --> U
  A([Agente IA<br/>MCP / CLI]) -- slug+password, tool calls, propose --> K
  K -- results, confirm links --> A
  AD([Admin]) -- suspend / reactivate, read users, ponds, audit, totals --> K
  P([Pasarela de pago<br/>simulated provider]) -- payment confirmed / failed --> K
  K -- charge request --> P
  N([Nodo / Oracle VM<br/>node-agent + Docker]) -- job claims, results, samples, heartbeats --> K
  K -- jobs: create/start/stop/backup/restore/delete --> N
  E([Resend email]) 
  K -- verify, reset, notifications --> E
  E -- links clicked by user --> U
```

## Level 1: subsystems

```mermaid
flowchart TB
  subgraph KoiCloud
    AUTH[1 Auth & session<br/>auth/, core/auth.py]
    PONDS[2 Ponds<br/>modules/ponds]
    BK[3 Backups<br/>modules/backups]
    SQL[4 SQL console<br/>modules/sql_console]
    BILL[5 Usage, billing & plans<br/>modules/billing, metering]
    AG[6 Agent access & confirm<br/>modules/agent_access, mcp/, commands/confirmations]
    ADM[7 Admin<br/>modules/admin, commands/admin]
    WK[8 Provisioning workers<br/>modules/jobs, workers/reconciler, node-agent]
    NOTIF[9 Notifications<br/>modules/notifications]
  end
  AUTH -- AuthContext user_id, role --> PONDS & BK & SQL & BILL & AG & ADM
  BILL -- active plan, quota --> PONDS
  PONDS -- enqueue job --> WK
  BK -- backup / restore / pre_delete job --> WK
  WK -- observed_state, last_error --> PONDS
  WK -- backup row status --> BK
  WK -- samples size_bytes, container_state --> BILL
  SQL -- requires observed=running --> PONDS
  AG -- acts as owner User --> PONDS & SQL & BK & BILL
  AG -- confirmation token --> AUTH
  ADM -- user.status=suspended --> AUTH
  AUTH & BILL & PONDS -- events --> NOTIF
```

### Flows between subsystems

| Flow | From → To | Data / event | Code |
|---|---|---|---|
| F1 | Auth → all | bearer JWT (15 min) → `AuthContext` | `core/auth.py:get_current_user` |
| F2 | Billing → Ponds | active subscription / plan quota on create | `ponds/service.py` (`plan_required`, `quota_exceeded`) |
| F3 | Ponds/Backups → Workers | `jobs` row queued (one active per pond) | `_assert_no_active_job`, `jobs/service.py` |
| F4 | Workers → Ponds/Backups | job result → `pond_status.observed_state`, backup status | `jobs/service.py`, node-agent handlers |
| F5 | Workers → Billing | `pond_samples` → daily `instance_hours`, `storage_gb_hours` | `metering/service.py` |
| F6 | Agent → everything | slug+password → owner `User` (full owner scope) | `agent_access/service.py:authenticate` |
| F7 | Admin → Auth | `users.status = suspended` | `commands/admin.py:suspend_user` |
| F8 | * → Notifications | verify/reset/pond/billing emails via Resend | `notifications/` |
| F9 | Payment → Billing | `confirm_payment` → subscription active, invoice paid | `billing/service.py`, `payments/simulated.py` |

## Cross-subsystem invariants (model `System.tla`)

| Rule | Plain sentence | main @ 72015b5 |
|---|---|---|
| NoPondApiWhenLoggedOut | After you log out, no pond call with your old access token works. | holds: logout stores the access `jti` and `get_current_user` rejects it with 401 `token_invalid` |
| NoPondApiWhenSuspended | A suspended user cannot reach any pond API. | **breaks**: `get_current_user` hard-codes `status=ACTIVE`; suspend revokes nothing |
| AgentScopeWithinOwner | The agent can never do what its owner can't. | **breaks**: `agent_access.authenticate` does not check `user.status` |
| DeletedPondHasNoJobs | A deleted pond has no job in flight. | holds |
| DeletedPondAccruesNoUsage | A deleted pond adds no billed hours. | **breaks**: `compute_day_metrics` counts the tail after the last sample as running when that sample was running |

Shortest paths (from `/statechart` on `SystemAsIs.cfg`):
- NoPondApiWhenLoggedOut holds. The path that used to break was log in → log out (access still live) → the pond API answers. Logout now clears the access token, so that call is refused.
- NoPondApiWhenSuspended: log in → admin suspends you → the pond API still answers.
- AgentScopeWithinOwner: log in → suspended → agent on → agent creates a pond.
- DeletedPondAccruesNoUsage: create → online → node sample (running) → delete → deleted → daily metering bills the rest of the day.

Fixed model (`SystemFixed.cfg`): 88 states, all rules hold. Not modelled: multiple users/nodes, refresh-token rotation races, payment webhooks, email delivery failures.
