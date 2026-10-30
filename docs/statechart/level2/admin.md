# L2 · 7 Admin
Code: `apps/api/app/modules/admin/service.py`, `commands/admin.py`, web `features/admin/`.
```mermaid
stateDiagram-v2
  [*] --> Active
  Active --> Suspended: suspend (type SUSPENDER, reason → audit)
  Active --> Active: wrong confirm text → 409
  Suspended --> Active: reactivate
```
| # | From | Event | Guard | To | Side effect | e2e test |
|---|---|---|---|---|---|---|
| D1 | Active | suspend | admin, text=SUSPENDER | Suspended | audit `suspend_user` + reason; tokens revoked; agent blocked | `admin: suspended user loses api access` |
| D2 | Active | suspend | wrong text | Active | 409 | `admin: suspend needs typed confirm` |
| D3 | Suspended | reactivate | admin | Active | audit | `admin: reactivate restores login` |
| D4 | — | any /admin/* | non-admin | — | 403 admin_only | `admin: non-admin gets 403` |
| D5 | — | totals | admin | — | global counts | `admin: totals are global` |
