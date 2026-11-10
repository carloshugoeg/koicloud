# Pond temporary access statechart (issue #203 / S2 demo)

Agreed behavior for a pond-scoped, expiring, revocable credential (link + password),
plus the **bound temp SQL confirmation** follow-on (TEMP-CONFIRM).

| File | Role |
|---|---|
| `PondToken.tla` | TLA+ model (credential lifecycle) |
| `PondToken.cfg` | TLC config (credential invariants) |
| `PondToken.view.mjs` | Reader labels for the credential chart |
| `pond-temp-access.mmd` | Mermaid chart from TLC (credential) |
| `report.md` | TLC verdict (credential) |
| `TempSqlConfirm.tla` | TLA+ model (propose → confirm → claim/admit) |
| `TempSqlConfirm.cfg` | TLC config (binding / at-most-once invariants) |
| `TempSqlConfirm.view.mjs` | Reader labels for the confirmation chart |
| `temp-sql-confirm.mmd` | Mermaid chart from TLC (confirmation) |
| `report-temp-sql-confirm.md` | TLC verdict (confirmation) |

## States the reader cares about (credential)

- **Issued** — presenter created the token; plaintext password shown once; only the hash is stored.
- **Active** — audience authenticated; actor pinned to that `pond_id`.
- **Expired** — `expires_at` in the past.
- **Revoked** — presenter set `revoked_at`.

## States the reader cares about (temp SQL confirmation)

- **NoProposal** — live credential, no pending write challenge.
- **Pending** — bound `run_sql_write` proposal stored with `pond_token_id` + pond + digest.
- **Consumed** — durable claim (terminal). Includes SQL success, SQL failure, and revoke/expire after claim before admit. Never returns to Pending.

Credential is independently Live / Expired / Revoked. Logical session identity is `PondToken.id`. Holders of the same link/password are the same principal (no device isolation).

## Paths that can break (must stay denied)

These are the transitions tests must assert. HTTP for auth failures is **401**.

1. **Use after expiry** — Expired → Expired (use denied); MCP auth stays 401.
2. **Use after revoke** — Revoked → Revoked (use denied); MCP auth stays 401.
3. **Wrong password** — Issued/Active → *(wrong password)*; auth 401; hash unchanged.
4. **Wrong pond** — Active → Active (wrong pond denied); cannot see or act on another pond.
5. **Forbidden tool** — Active → Active (create/delete denied); `create_pond` / `delete_pond` (and other lifecycle tools) fail for this actor.
6. **Plaintext leak** — create returns the secret once; list/revoke/DB never store or return plaintext.
7. **SQL privilege** — `run_sql` for this actor uses the same non-superuser console path as the web console (depends on #198 / `koi_console`).
8. **Cross-session confirm** — Pending → Pending (denied); another `PondToken` for the same owner+pond cannot confirm.
9. **Owner / temp side doors** — temp cannot confirm owner rows; owner JWT/full MCP cannot confirm or discard temp-bound rows.
10. **Replay / dual claim** — Consumed → Consumed (denied); at most one durable claim across workers.
11. **Revoke before admit** — claim then revoke/expire before final admission: token spent, SQL never runs.

## Invariants that hold (TLC)

Credential (`PondToken`): `AuthOkImpliesUsable`, `AuthOkImpliesNotExpired`, `AuthOkImpliesNotRevoked`, `AuthOkImpliesPasswordMatch`, `ToolOkImpliesAuthedActive`, `ToolOkImpliesAllowedOnPinnedPond`, `ForbiddenToolNeverOk`, `OtherPondNeverOk`, `ExpiredNeverAuthOk`, `RevokedNeverAuthOk`.

Confirmation (`TempSqlConfirm`): `ExecutedImpliesClaimed`, `ExecutedImpliesAdmitted`, `ExecutedImpliesConsumed`, `OkImpliesNoDenial`, `ReplayNeverOk`, `ConsumedNeverPending`, `DeadCredNeverOk`, `RevokeBeforeAdmitNeverExecutes`, `BindingDenialNeverClaims`, `AtMostOneSuccess`.

## Reproduce

```sh
TLA2TOOLS=/path/to/tla2tools.jar JAVA=java \
  <pstack>/skills/statechart/scripts/statechart \
  PondToken.tla --config PondToken.cfg --view PondToken.view.mjs --out /tmp/pond-token-out

TLA2TOOLS=/path/to/tla2tools.jar JAVA=java \
  <pstack>/skills/statechart/scripts/statechart \
  TempSqlConfirm.tla --config TempSqlConfirm.cfg --view TempSqlConfirm.view.mjs --out /tmp/temp-sql-confirm-out
```

Model leaves out: password hashing algorithm, HTTP status codes as numbers, concurrent revoke-during-auth races at the TCP layer, and the #198 console-role setup inside the pond DB. Confirmation model leaves out multi-worker scheduling details (claim is still modeled as a single atomic step).
