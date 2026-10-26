---
id: W1-27
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-plans-pricing
epica: E2-01
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/123"
depends_on:
---

# [W1-27] Plan pricing from `GET /plans` (issue #96 amendment)

Tracked from the pricing amendment comment on
[#96](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428592682).
**HIGH-RISK (money):** preview only; Carlos merges himself. Do not auto-merge.
The OpenAPI `PlanOut` change is frozen-contract work — Carlos decides CCR/merge; this
ticket does **not** claim a CCR was approved.

## Qué se ve

- `GET /plans` returns `billing_model` (`monthly` | `hourly`), `unit_price` and `currency`
  for every plan (Pro hourly included).
- The web app formats every catalog price with one shared `formatPrice(plan)` on landing,
  plan cards, comparison table, checkout invoice preview, and any surface that shows a
  plan catalog amount.
- Pro never renders as `USD 0.00`; it shows the API `unit_price` (e.g. `USD 0.02` / hora).
- No hard-coded catalog prices remain in production UI source (including `USD 0.02`).

## Entradas ya decididas (no se cambian)

- Keep `price_monthly_usd` for subscribe invoice math; display fields are additive.
- Shared helper: `apps/web/src/lib/format-price.ts` (`formatPrice` + period helpers).
- API mapping: `apps/api/app/modules/billing/plan_pricing.py`.
- **Known hard-code (API, not UI):** `PRO_HOURLY_UNIT_PRICE_USD = Decimal("0.02")` in
  `plan_pricing.py` supplies Pro’s display `unit_price` when `postpaid` is true. It is
  intentionally **not** stored in `price_monthly_usd` so subscribe invoices for Pro stay
  at `$0` on signup. A later seed/column change can replace this constant; out of scope
  for this PR (no further PlanOut / schema churn).
- Regenerate with `make contracts` (`openapi.json` + `schema.d.ts`).
- Branch: `w1-plans-pricing`. PR: [#123](https://github.com/carloshugoeg/koicloud/pull/123).

## Criterios de aceptación

1. `PlanOut` / `GET /plans` includes `billing_model`, `unit_price`, `currency` for sandbox,
   micro and pro (Pro = `hourly` + non-zero `unit_price`).
2. One shared `formatPrice` is used on landing, plan cards, comparison table and checkout.
3. No hard-coded catalog price literals in production UI (`no-hardcoded-prices` test fails
   if they return).
4. `/app/planes` cards/comparison and checkout show the same Pro price that `GET /plans`
   returns (see **E2E justification** below).
5. `make check-web` green; API pricing tests green; OpenAPI regenerated.
6. Before/after screenshots under `media/plans-pricing/` show Pro as `USD 0.02` / hora,
   never `USD 0.00`.

## E2E justification (MSW Vitest, not preview browser)

`apps/web/src/features/plans/plans-pricing.e2e.test.tsx` is the e2e check for CA4.

**Why not a live preview browser e2e:** the Vercel web preview has empty
`VITE_API_BASE_URL`, so `GET /api/v1/plans` is rewritten to the SPA HTML shell
(`200 text/html`, starts with `<!doctype`). There is no control-plane API on that host
to return JSON `unit_price`. A Playwright script against the preview therefore cannot
compare UI text to a real `GET /plans` body.

**What we do instead:** the Vitest + MSW test overrides `GET /plans` with a distinctive
Pro `unit_price` (`0.0875`, not the historical `0.02` literal), renders `/app/planes`,
opens Pro checkout, and asserts card + comparison + checkout all show
`formatPrice` of that same API value. Manual before/after screenshots under
`media/plans-pricing/` (Vite + MSW after; `main` worktree before) show Pro as
`USD 0.02 / hora` and never `USD 0.00`.

## No tocar

- Further PlanOut / OpenAPI churn beyond this PR’s already-exported fields.
- Payment provider / subscribe invoice totals (except reading `unit_price` for preview).
- Sibling PRs (screen-map, admin suspend-reason) file sets.
- Production deploy / merge without Carlos.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos ni precios de catálogo.

## Referencia

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428592682)
pricing amendment comment. Pattern: W3-06 planes + W2-03 checkout screens.
