# Temp-access SQL auto-confirm statechart (issue #205 / S4 demo)

Agreed behavior for `run_sql` when the actor is a pond temporary-access
credential: safe DDL/DML auto-confirms, dangerous statements never run, long
queries hit `statement_timeout`, and a per-token rate limit throttles bursts.
Account (non-temp) actors keep the existing `propose → confirm` path.

| File | Role |
|---|---|
| `TempSqlAutoconfirm.tla` | TLA+ model |
| `TempSqlAutoconfirm.cfg` | TLC config (invariants) |
| `TempSqlAutoconfirm.view.mjs` | Reader labels for the chart |
| `temp-sql-autoconfirm.mmd` | Mermaid chart from TLC |
| `report.md` | TLC verdict |

## States the reader cares about

- **Idle (temp actor)** — pond token authenticated; ready for `run_sql`.
- **Idle (account actor)** — full MCP/CLI actor; writes still need confirm.
- **Confirm write (account)** — `confirmation_required`; waiting on `confirm_action`.
- **Running (temp auto-confirm)** — safe `CREATE TABLE` / `INSERT` executing with no confirm round-trip.
- **Blocked (dangerous SQL)** — `DROP DATABASE` / `DROP ROLE` / `ALTER SYSTEM` / `COPY ... PROGRAM` rejected.
- **Blocked (privilege change)** — `GRANT` / `REVOKE` / `ALTER ROLE` rejected.
- **Running (long query)** — statement started under temp access.
- **Timed out** — `statement_timeout` aborted the query.
- **Rate limited** — per-token window exhausted; further calls throttled until reset.
- **Success** — rows (or empty write result) returned.

## Paths that can break (must stay enforced)

These are the transitions tests must assert.

1. **Temp auto-confirm** — Idle (temp) → Running (temp auto-confirm) → Success for safe `CREATE TABLE` / `INSERT`. No `confirm_action` round-trip.
2. **Account confirm unchanged** — Idle (account) → Confirm write → (confirm_action) → Running → Success. First write call stays `confirmation_required`.
3. **Dangerous blocked** — Idle (temp) → Blocked for `DROP DATABASE`, `DROP ROLE`, `ALTER SYSTEM`, `COPY ... PROGRAM`. No execution.
4. **Privilege blocked** — Idle (temp) → Blocked for `GRANT` / `REVOKE` / `ALTER ROLE`. No execution.
5. **Timeout** — Idle (temp) → Running (long query) → Timed out via `statement_timeout`.
6. **Rate limit** — Idle (temp) → Rate limited once the per-token window is exceeded; later calls stay throttled until the window resets.

## Invariants that hold (TLC)

`TypeOK`, `AccountRunningImpliesPriorConfirm`, `DangerousNeverExecutes`,
`PrivilegeNeverExecutes`, `TempSafeWriteNeverConfirms`,
`RateLimitMeansNotExecuted`, `LongRunningNeverSucceeds`.

## Reproduce

```sh
TLA2TOOLS=/path/to/tla2tools.jar JAVA=java \
  <pstack>/skills/statechart/scripts/statechart \
  TempSqlAutoconfirm.tla --config TempSqlAutoconfirm.cfg \
  --view TempSqlAutoconfirm.view.mjs --out /tmp/temp-sql-autoconfirm-out
```

Model leaves out: SQL parsing edge cases (comments, dollar-quoting), concurrent
requests racing the rate window, and the #198 `koi_console` non-superuser role
inside the pond DB. Rate-limit window size is a constant (`MaxRate`) in the
model; production picks a concrete limit and window length.
