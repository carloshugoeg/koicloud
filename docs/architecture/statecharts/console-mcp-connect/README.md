# Console MCP connect statechart (issue #204 / S3 demo)

Agreed behavior when an audience member pastes a temporary pond link + password into a
console agent (Claude Code, Cursor CLI, or Codex CLI) and calls MCP tools.

This chart is the **client connect** view. Token lifecycle (issue, expire, revoke) lives in
[`../pond-temp-access/`](../pond-temp-access/). Do not copy PR #198 (SQL console role).

| File | Role |
|---|---|
| `ConsoleConnect.tla` | TLA+ model |
| `ConsoleConnect.cfg` | TLC config (invariants) |
| `ConsoleConnect.view.mjs` | Reader labels for the chart |
| `console-mcp-connect.mmd` | Mermaid chart from TLC |
| `report.md` | TLC verdict |

## States the reader cares about

- **No credentials** — agent has no temp link/password yet.
- **Link pasted** — slug + password are in the client config; auth not finished.
- **Auth failed** — Basic auth rejected (401 `agent_bad_credentials`).
- **Pond-pinned** — auth succeeded; `AuthContext.pond_id` fixed; tools limited to
  `TEMP_ACCESS_TOOLS` (`whoami`, `get_pond`, `run_sql`).
- **Pond-pinned (read ok)** — `whoami` or `get_pond` on the pinned pond succeeded.
- **Pond-pinned (forbidden denied)** — lifecycle tool rejected; session stays pinned.
- **Pond-pinned (off-pond denied)** — other pond rejected; session stays pinned.

## Paths that can break (must stay denied)

1. **Wrong password** — Link pasted → Auth failed [401]; never pond-pinned.
2. **Tool before auth** — call without `lastAuth=ok` → tool denied.
3. **Forbidden tool** — `create_pond` / `delete_pond` / other non-allowlisted tools denied
   while still pond-pinned.
4. **Off-pond** — `get_pond` for another pond denied while still pond-pinned.
5. **list_tables** — not in `TEMP_ACCESS_TOOLS` on this base; prefer `whoami` or `get_pond`
   for smoke (S5 / #206 lands `list_tables` later).

## Invariants that hold (TLC)

`AuthOkImpliesPinned`, `AuthOkImpliesPasswordMatch`, `AuthFailNeverPinned`,
`ToolOkImpliesPinned`, `ToolOkImpliesAllowed`, `ForbiddenNeverOk`, `OtherPondNeverOk`,
`UnauthedNeverToolOk`, `PinnedStaysPinnedAfterTool`.

## Reproduce

```sh
TLA2TOOLS=/path/to/tla2tools.jar JAVA=java \
  <pstack>/skills/statechart/scripts/statechart \
  ConsoleConnect.tla --config ConsoleConnect.cfg --view ConsoleConnect.view.mjs \
  --out /tmp/console-connect-out
```

Model leaves out: per-client config file syntax, Streamable HTTP vs JSON-RPC transport
differences, revoke/expiry (covered by pond-temp-access), and `run_sql` auto-confirm (#205).
