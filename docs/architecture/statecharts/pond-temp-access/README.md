# Pond temporary access statechart (issue #203 / S2 demo)

Agreed behavior for a pond-scoped, expiring, revocable credential (link + password).

| File | Role |
|---|---|
| `PondToken.tla` | TLA+ model |
| `PondToken.cfg` | TLC config (invariants) |
| `PondToken.view.mjs` | Reader labels for the chart |
| `pond-temp-access.mmd` | Mermaid chart from TLC |
| `report.md` | TLC verdict |

## States the reader cares about

- **Issued** — presenter created the token; plaintext password shown once; only the hash is stored.
- **Active** — audience authenticated; actor pinned to that `pond_id`.
- **Expired** — `expires_at` in the past.
- **Revoked** — presenter set `revoked_at`.

## Paths that can break (must stay denied)

These are the transitions tests must assert. HTTP for auth failures is **401**.

1. **Use after expiry** — Expired → Expired (use denied); MCP auth stays 401.
2. **Use after revoke** — Revoked → Revoked (use denied); MCP auth stays 401.
3. **Wrong password** — Issued/Active → *(wrong password)*; auth 401; hash unchanged.
4. **Wrong pond** — Active → Active (wrong pond denied); cannot see or act on another pond.
5. **Forbidden tool** — Active → Active (create/delete denied); `create_pond` / `delete_pond` (and other lifecycle tools) fail for this actor.
6. **Plaintext leak** — create returns the secret once; list/revoke/DB never store or return plaintext.
7. **SQL privilege** — `run_sql` for this actor uses the same non-superuser console path as the web console (depends on #198 / `koi_console`).

## Invariants that hold (TLC)

`AuthOkImpliesUsable`, `AuthOkImpliesNotExpired`, `AuthOkImpliesNotRevoked`, `AuthOkImpliesPasswordMatch`, `ToolOkImpliesAuthedActive`, `ToolOkImpliesAllowedOnPinnedPond`, `ForbiddenToolNeverOk`, `OtherPondNeverOk`, `ExpiredNeverAuthOk`, `RevokedNeverAuthOk`.

## Reproduce

```sh
TLA2TOOLS=/path/to/tla2tools.jar JAVA=java \
  <pstack>/skills/statechart/scripts/statechart \
  PondToken.tla --config PondToken.cfg --view PondToken.view.mjs --out /tmp/pond-token-out
```

Model leaves out: password hashing algorithm, HTTP status codes as numbers, concurrent revoke-during-auth races, and the #198 console-role setup inside the pond DB.
