---
id: W1-18
workstream: W1
persona: Carlos
estado: hecho
rama: w1-demo-vivo-s3
epica: "E9-06"
sprint: S3
pr: https://github.com/carloshugoeg/koicloud/pull/75
depends_on:
---

# [W1-18] Demo vivo S3 — subscribe → usage → PDF+IVA → backup → restore

## Qué se ve

`scripts/demo-vivo.sh` gana subcomandos `s3` / `s3-entrega` que ejercitan el happy path
de Avance 50 % contra la **API real** (post-seed): contratar Micro, ver uso, descargar
factura PDF con IVA, backup on-demand y restore. El runbook documenta el camino y los
gaps honestos (pago simulado, usage en 0 en ensayo fresco).

## Entradas ya decididas (no se cambian)

- Creds seed: `demo@koicloud.dev` / `Sup3rSegura!2026` (igual que Demo B).
- G1 persiste subscribe/invoice/payment; W3-09/10 renderizan PDF con IVA 12 %.
- W1-10 backups/restore y W1-11 metering ya en `main`.
- No fixtures de invoice; `payment.method=simulated` es el port real.

## Criterios de aceptación

1. `scripts/demo-vivo.sh` expone `s3` y `s3-entrega` (`reset` → `s3`).
2. `s3` llama API real: `POST /subscriptions` → `GET /usage` → `GET /invoices/{id}/pdf`
   → `POST …/backups` → `POST …/restore`, con seed + login demo.
3. Subscribe aserta invoice persistida (`KC-…`, IVA > 0, `payment.method=simulated`).
4. PDF: bytes `%PDF` (>1 KB) y texto con IVA/12/KC- vía extracción de streams (o
   `pdftotext`), no grep crudo que falle con FlateDecode; cruce con invoice JSON.
5. `docs/runbooks/demo-vivo.md` documenta el camino S3, gaps honestos, y que `full`
   exige pago simulado + factura `paid`.
6. Ningún paso del happy path depende de fixtures de invoice/usage/backup.

## No tocar

OpenAPI, `apps/web/**`, workers de renovación, pack de presentación del store.
W1-17 (reconciler) es ticket aparte.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

`docs/runbooks/demo-vivo.md` § S3 · issue #11 plano S3 · W1-14 (guion base ya en `main`).
