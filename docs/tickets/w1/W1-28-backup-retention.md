---
id: W1-28
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-backup-retention
epica: "E2-01"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/124"
depends_on:
---

> **ID note:** briefly mislabeled as W1-27; that ID belongs to
> [#123](https://github.com/carloshugoeg/koicloud/pull/123) (`W1-27-plans-pricing`).
> This ticket is **W1-28**.

# [W1-28] `PlanOut.backup_retention_days` (constante, A3)

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96) amendment A3
([comment](https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428918452)).
**Ruta de constante server-side.** Sin migración ni columna en `plans` (alta riesgo).

## Qué se ve

- `GET /plans` incluye `backup_retention_days` por plan (sandbox `0`, micro `7`, pro `30`).
- Solo la fila «Respaldos automáticos» de la tabla comparativa en `/app/planes` lee ese
  campo. Las viñetas de las tarjetas de plan quedan como antes (Micro «Respaldos diarios
  (7 d)», Pro «Hasta 10 ponds y 20 GB»).
- Ya no hay literales `Diarios (7 días)` / `Diarios (30 días)` en la tabla.

## Entradas ya decididas (no se cambian)

- Constante en `apps/api/app/modules/billing/plan_retention.py` (mapa por `plan.id`).
- Campo nuevo en `PlanOut`: `backup_retention_days: int` (OpenAPI regenerado con
  `make contracts`).
- Sin `price_hourly_usd` aquí: el pricing de catálogo vive en #123.
- **CCR:** OpenAPI/`PlanOut` es contrato congelado. El comentario A3 del issue #96 vía
  Cursor **no** cuenta como CCR de Carlos. Este PR **no** declara CCR aprobado; hace
  falta CCR propio de Carlos antes de merge.
- Rama: `w1-backup-retention`. Rebase/coordina con #123 (ambos editan `PlanOut`).

## Criterios de aceptación

1. `GET /plans` responde `backup_retention_days` para sandbox/micro/pro = `0`/`7`/`30`.
2. No hay migración Alembic ni columna nueva en `plans`.
3. La tabla «Respaldos automáticos» no hard-codea `Diarios (7 días)` / `Diarios (30 días)`.
4. Las viñetas de tarjeta Pro/Micro/Sandbox conservan el texto anterior a este ticket.
5. Pruebas API + Vitest verdes; `make check-web` (y API relevante) verde.
6. Capturas before/after desktop + 375 px en `media/a3-backup-retention/` y en el PR.

## No tocar

- Migraciones Alembic / columnas de `plans`.
- El alcance completo de #123 (`w1-plans-pricing`): `billing_model`, `unit_price`,
  `formatPrice`, etc.
- Ítems HIGH del amendment (A2, A5, A6, A7).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
Sin CCR de Carlos para el cambio OpenAPI, no merges. No inventes columnas ni endpoints
fuera de A3.

## Referencia

Imitá el PR de pricing [#123](https://github.com/carloshugoeg/koicloud/pull/123) en
estructura de contratos regenerados + pruebas + `media/`, sin fusionar ni copiar su
diff de precios.
