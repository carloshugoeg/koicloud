# Contracts changelog

- 2026-10-27 · CCR #135 · `BackupOut.expires_at` (datetime \| null, derived; no column). Null when status≠succeeded or kind=pre_delete; else created_at + 7 days UTC. No migration. Does not land `PlanOut.backup_retention_days`.
- 2026-10-27 · CCR #151 PlanOut pricing · `PlanOut.currency` is the single-value enum `"USD"`; `unit_price` quantized to 4 decimals server-side. Pro hourly rate is one shared constant (`PRO_HOURLY_UNIT_PRICE_USD`) for GET /plans and metering. No migration.
- 2026-10-27 · CCR #131 · `POST /ponds/{id}/stop` (`stop_pond`) and `POST /ponds/{id}/start` (`start_pond`) → `202 {pond, job}`. No migration.
- 2026-10-26 · Issue #96 pricing amendment · `PlanOut` gains `billing_model` (`monthly`|`hourly`), `unit_price`, and `currency` on `GET /plans`. Display-only; `price_monthly_usd` and subscribe invoice math unchanged.
- 2026-10-26 · CCR #125 admin suspend reason · `SuspendUserRequest.reason` optional (trim, max 500) stored in `audit_events.metadata.reason`. Error catalog gains `user_not_found` (404). No migration.
- 2026-10-26 · Issue #96 amendment A1 · `PondOut.size_bytes`, `AdminPondOut.size_bytes` + `last_error`, `SubscriptionOut.invoice_id`, and `GET /admin/totals` (`admin_get_totals`). No migration.
- 2026-10-09 · CCR #66 G1 payment port · OpenAPI `SubscriptionStatus` gains `pending_payment`. `payments` gains `provider` + `provider_ref` (unique together). Invoice plano status `open` maps to existing `issued` (no new invoice enum).
- 2026-09-25 · CCR CLI missing-session exit · Frozen to `1` per `api-surface.md` §5 (not matrix `2`). No schema change.
- 2026-09-24 · CCR verify token transport · Docs and tickets aligned to existing OpenAPI body JSON `VerifyEmailRequest`; no schema change.
- 2026-09-22 · Phase 0 freeze · Initial OpenAPI export generated from `apps/api`.
