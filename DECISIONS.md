# Decisions

Accepted CCR decisions (amendment r3). Longer A-01..A-12 records live in [`docs/adr/`](docs/adr/).
Source: [#96 comment](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6445716121).

## Soft-delete users (#126)

**Decision:** `deleted_at` plus an email tombstone.

**Why:** keeps FKs, invoices and audit intact.

**Rejected:** hard delete (breaks FKs) and `suspended` as delete (email not freed, ponds and subs not cancelled).

## Invoice NIT snapshot (#127)

**Decision:** `InvoiceOut.nit` is snapshotted from `users.nit` at issue time.

**Why:** the invoice must not change later.

**Rejected:** reading `/me` in the UI (the PDF and other clients would not see it).

## Pond stop/start via public API (#131)

**Decision:** desired-state write plus a job, with a 202 `{pond, job}`.

**Why:** reuses the existing reconciler, jobs and agent handlers.

**Rejected:** reconciler only (nothing writes `desired=stopped`) and a synchronous stop (would block on the node).

## Derived backup expiry (#135)

**Decision:** computed server-side from a constant of 7 days.

**Why:** keeps business math out of the web app and needs no migration.

**Rejected:** computing it in the browser and a new column (for now).
