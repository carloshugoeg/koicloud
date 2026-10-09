---
id: G2
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-g2-daily-renewal
epica: E2-04
sprint: S3
pr:
depends_on: G1
---

# [G2] Daily renewal worker (E2-04)

## Qué se ve

Un scheduler diario corre `python -m app.workers.daily_renewal`. Cada suscripción
`active` con `current_period_end` vencido se cierra si `cancel_at_period_end`, o
pasa por `BillingService.renew()` (factura + pago vía el payment port) si no.
No hay un camino de pago paralelo.

## Entradas ya decididas (no se cambian)

- G1 landed `BillingService.renew` through `PaymentProvider.start_payment` + shared
  `confirm_payment` ([plano comment 6084286411](https://github.com/carloshugoeg/koicloud/issues/11#issuecomment-6084286411)).
- Pattern: same once-per-run style as `workers/daily_backups.py` / `daily_usage.py`.
- Simulated provider confirms in-process; a future Stripe-style adapter confirms via
  webhook and the worker may skip provider-managed subs later (out of scope today).
- Prod compose worker loop also runs this module hourly alongside backups/usage.

## Criterios de aceptación

1. Worker module `apps/api/app/workers/daily_renewal.py` with `run` / `tick` / `__main__`.
2. Due + `cancel_at_period_end` → `status=canceled`; no new invoice.
3. Due without cancel → `BillingService.renew` → new paid invoice + active period (simulated).
4. In-period active subscriptions are left alone; second tick is a no-op.
5. Uses advisory lock so two overlapping runs do not double-renew.
6. `pytest tests/test_daily_renewal.py` green.
7. Prod compose worker invokes `python -m app.workers.daily_renewal`.

## No tocar

`apps/web/**`, OpenAPI/schemas congelados, migraciones nuevas, adapters de pago reales.

## Si algo falta

Si hace falta editar un contrato congelado → `BLOQUEADO`. No inventar schema de invoice.

## Referencia

`apps/api/app/workers/daily_backups.py`, `BillingService.renew`, feature-breakdown E2-04.
