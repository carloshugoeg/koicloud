---
id: W1-28
workstream: W1
persona: Carlos
estado: cerrado
rama: w1-backup-retention
epica: "E2-01"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/124"
depends_on:
---

> **ID note:** briefly mislabeled as W1-27; that ID belongs to [#123](https://github.com/carloshugoeg/koicloud/pull/123) plans pricing. Renumbered to W1-28. PR #124 stays **closed**; Wave A1 owns retention + hourly.

# [W1-28] `PlanOut.backup_retention_days` (constante, A3)

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96) amendment A3
([comment](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428918452)).
**Ruta de constante server-side.** Sin migración ni columna en `plans` (alta riesgo).

## Qué se ve

- `GET /plans` incluye `backup_retention_days` por plan (sandbox `0`, micro `7`, pro `30`).
- La tabla «Respaldos automáticos» en `/app/planes` lee ese campo; ya no hay literales
  `Diarios (7 días)` / `Diarios (30 días)` en `plans-page.tsx`.

## Entradas ya decididas (no se cambian)

- Constante en `apps/api/app/modules/billing/plan_retention.py` (mapa por `plan.id`).
- Campo nuevo en `PlanOut`: `backup_retention_days: int` (OpenAPI regenerado con
  `make contracts`).
- Sin `price_hourly_usd` aquí: el pricing de catálogo vive en #123 (`unit_price` /
  `billing_model`); no se roba ese PR.
- CCR: el amendment A3 del issue #96 (misma forma que #123 usó el amendment de pricing).
- Rama: `w1-backup-retention`.

## Criterios de aceptación

1. `GET /plans` responde `backup_retention_days` para sandbox/micro/pro = `0`/`7`/`30`.
2. No hay migración Alembic ni columna nueva en `plans`.
3. `plans-page.tsx` no contiene los literales `Diarios (7 días)` ni `Diarios (30 días)`.
4. Pruebas API + Vitest verdes; `make check-web` (y API relevante) verde.
5. Capturas before/after desktop + 375 px en el store media y enlazadas en el PR.

## No tocar

- Migraciones Alembic / columnas de `plans`.
- El alcance completo de #123 (`w1-plans-pricing`): `billing_model`, `unit_price`,
  `formatPrice`, etc.
- Ítems HIGH del amendment (A2, A5, A6, A7).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes columnas ni endpoints fuera de A3.

## Referencia

Imitá el PR de pricing [#123](https://github.com/carloshugoeg/koicloud/pull/123) en
estructura de contratos regenerados + pruebas, sin fusionar ni copiar su diff de precios.
