# Invitar agente dialog statechart (issue #208 / S7 demo)

Agreed UI behavior for the presenter dialog on pond detail: create a temporary
link + password (S2), show password once, show QR + console paste instructions
(S3), hide plaintext on revisit, revoke so MCP auth fails.

Token lifecycle (issue/expire/revoke storage) lives in
[`../pond-temp-access/`](../pond-temp-access/). Console paste connect lives in
[`../console-mcp-connect/`](../console-mcp-connect/). This chart is the
**presenter dialog** view only.

| File | Role |
|---|---|
| `InviteAgent.tla` | TLA+ model |
| `InviteAgent.cfg` | TLC config (invariants) |
| `InviteAgent.view.mjs` | Reader labels for the chart |
| `invitar-agente.mmd` | Mermaid chart from TLC |
| `report.md` | TLC verdict |

## States the reader cares about

- **Closed** — dialog not open; password not in the DOM.
- **Dialog open** — idle; no invite generated yet in this open.
- **Password shown once** — create just returned; plaintext password + QR +
  Claude Code / Cursor CLI / Codex CLI paste instructions visible.
- **Subsequent view (password hidden)** — reopen with an active token; QR and
  paste instructions remain; plaintext password is not re-displayed.
- **Revoked** — presenter revoked; invite UI cleared.
- **Revoked (MCP auth fails)** — after revoke, MCP Basic auth stays denied.

## Paths that can break (must stay denied)

These are the transitions tests must assert.

1. **Plaintext on revisit** — Subsequent view must never show the password
   (list/API never returns it; UI must not stash it across closes as a reveal).
2. **Password after close** — Closed → password not visible.
3. **Use after revoke** — Revoked → MCP auth fails (`401 agent_bad_credentials`).
4. **Auth ok without usable token** — AuthOkImpliesUsable; create is the only
   way to make the token usable in this chart.
5. **Missing QR/snippets on active invite** — open_created and open_revisit must
   show QR and the three console paste instructions.

## Invariants that hold (TLC)

`PasswordOnlyOnCreate`, `RevisitHidesPassword`, `ClosedHidesPassword`,
`InviteShowsQrAndSnippets`, `RevokedNeverAuthOk`, `AuthOkImpliesUsable`.

## Reproduce

```sh
TLA2TOOLS=/path/to/tla2tools.jar JAVA=java \
  <pstack>/skills/statechart/scripts/statechart \
  InviteAgent.tla --config InviteAgent.cfg --view InviteAgent.view.mjs \
  --out /tmp/invitar-agente-out
```

Model leaves out: create HTTP errors, expiry wall-clock (covered by pond-temp-access),
QR encoding algorithm, focus/Esc a11y, and ChatGPT/claude.ai web (out of scope).
