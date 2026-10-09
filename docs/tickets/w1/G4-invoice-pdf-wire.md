---
id: G4
workstream: W1
persona: Carlos
estado: en_revision
rama: w1-g4-invoice-pdf-wire
epica: "E2-03"
sprint: S3
pr: https://github.com/carloshugoeg/koicloud/pull/50
depends_on: W3-09
---

# [G4] Wire `get_invoice_pdf` to the W3-09 renderer

## Qué se ve

`GET /invoices/{id}/pdf` downloads a real IVA PDF (Helvetica, academic footer) instead of placeholder bytes.

## Entradas ya decididas (no se cambian)

- Command: `get_invoice_pdf` in `apps/api/app/commands/billing.py`.
- Renderer: `render_invoice_pdf` from W3-09.
- Fixture-backed invoice until G1 persistence. Owner of an invoice id is the first caller.

## Criterios de aceptación

1. Response bytes start with `%PDF` and weigh more than 1 KB.
2. Extracted text includes `IVA`, `12`, and the academic footer.
3. A second user asking for the same invoice id gets `not_owner`.

## No tocar

- `apps/web/**`, `apps/api/app/workers/**`, frozen OpenAPI.

## Si algo falta

G1 replaces the in-memory fixture map with persisted invoices.

## Referencia

Plano S3 gap G4 on issue #11.
