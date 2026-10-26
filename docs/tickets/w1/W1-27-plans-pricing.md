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

Amendment approved by Carlos on
[#96](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428592682).
**HIGH-RISK (money):** preview only; Carlos merges himself. Do not auto-merge.

## Qué se ve

- `GET /plans` returns `billing_model` (`monthly` | `hourly`), `unit_price` and `currency`
  for every plan (Pro hourly included).
- The web app formats every catalog price with one shared `formatPrice(plan)` on landing,
  plan cards, comparison table, checkout invoice preview, and any surface that shows a
  plan catalog amount.
- Pro never renders as `USD 0.00`; it shows the API `unit_price` (e.g. `USD 0.02` / hora).
- No hard-coded catalog prices remain in production UI source (including `USD 0.02`).

## Entradas ya decididas (no se cambian)

- Contract change authorized by the #96 pricing amendment (CCR via Carlos).
- Keep `price_monthly_usd` for subscribe invoice math; display fields are additive.
- Shared helper: `apps/web/src/lib/format-price.ts` (`formatPrice` + period helpers).
- API mapping: `apps/api/app/modules/billing/plan_pricing.py`.
- Regenerate with `make contracts` (`openapi.json` + `schema.d.ts`).
- Branch: `w1-plans-pricing`. PR: [#123](https://github.com/carloshugoeg/koicloud/pull/123).

## Criterios de aceptación

1. `PlanOut` / `GET /plans` includes `billing_model`, `unit_price`, `currency` for sandbox,
   micro and pro (Pro = `hourly` + non-zero `unit_price`).
2. One shared `formatPrice` is used on landing, plan cards, comparison table and checkout.
3. No hard-coded catalog price literals in production UI (`no-hardcoded-prices` test fails
   if they return).
4. E2E-style check: `/app/planes` cards/comparison and checkout show the same Pro price
   that the mocked `GET /plans` returns.
5. `make check-web` green; API pricing tests green; OpenAPI regenerated.
6. Before/after screenshots under `media/plans-pricing/` show Pro as `USD 0.02` / hora,
   never `USD 0.00`.

## No tocar

- Payment provider / subscribe invoice totals (except reading `unit_price` for preview).
- Sibling PRs (screen-map, admin suspend-reason) file sets.
- Production deploy / merge without Carlos.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos ni precios de catálogo.

## Referencia

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428592682)
pricing amendment. Pattern: W3-06 planes + W2-03 checkout screens.
