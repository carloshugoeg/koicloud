---
id: G1
workstream: W1
persona: Carlos
estado: en_revision
rama: w1-g1-billing-persistence
epica: "E2-02, E2-03, E2-06"
sprint: S3
pr: https://github.com/carloshugoeg/koicloud/pull/54
depends_on: G4
ccr: https://github.com/carloshugoeg/koicloud/issues/66
---

# [G1] Billing persistence (invoices + payments)

## Qué se ve

Subscribe creates a real subscription, invoice (`KC-{year}-{seq:06d}`), and payment through the payment port. With `PAYMENT_PROVIDER=simulated`, confirmation runs in the same request so the API still returns active/paid/succeeded. List/get/cancel/pdf read from Postgres. IVA 12 % is included via `split_iva`.

## Entradas ya decididas (no se cambian)

- Tables already exist in `0001_initial`. This ticket adds ORM + command bodies + money precision + payment port columns.
- POST `/subscriptions` response shape stays `{subscription, invoice, payment}`.
- Plano invoice status `open` maps to existing OpenAPI/`issued` (no new invoice enum). CCR #66 adds `pending_payment` only.

## Criterios de aceptación

1. Subscribe persists subscription + invoice + payment via `PaymentProvider.start_payment` and shared `confirm_payment`.
2. Invoice numbers are unique per year (`invoices.number` unique + advisory lock + retry) with a concurrency test.
3. `get_invoice_pdf` reads the stored invoice (no fixture map).
4. `BillingService` receives the provider by injection and does not import adapters.
5. `BillingService.renew` exists as the G2 hook through the same port.

## No tocar

- Webhooks / real provider SDKs, `apps/web/**`, workers (full G2 is separate).

## Si algo falta

G2 daily renewal waits on this landing.

## Referencia

Plano S3 gap G1 on issue #11 (payment-port amendment comment 6084286411). CCR #66.
