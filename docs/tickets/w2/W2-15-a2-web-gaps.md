---
id: W2-15
workstream: W2
persona: Carlos
estado: en-curso
rama: w2-a2-web-gaps
epica: "E2-02 / E9-04 / E6 / E1"
sprint: S5
pr: ""
depends_on: []
---

# [W2-15] Wave A2 web gaps (endpoints existentes)

**Dueño:** Carlos Hugo Escobar (`@carloshugoeg`) — excepción cross-workstream sobre `apps/web/**`
(superficie W2) para cerrar gaps LOW del amendment r2 de #96 en paralelo a A1 API.

## Qué se ve

1. **Historial de suscripciones y cancelar al corte** en `/app/billing` (ya enrutada; deja de
   aliasar Uso). Lista `GET /subscriptions`. Cancelar llama `POST /subscriptions/{id}/cancel`
   con diálogo in-UI. Estados por `status` + `cancel_at_period_end`. Sin columna Factura
   (`invoice_id` no existe en `SubscriptionOut`).
2. **Checkbox de pago simulado** en el checkout: «Entiendo que el cobro es simulado…» debe
   marcarse para habilitar Contratar. Solo gate de cliente; el body sigue siendo `{ plan_id }`.
3. **Precios y retención sin hardcodes** en `plans-page` (y landing `formatPrice` compartido).
   `formatPrice(plan)` usa `price_monthly_usd` / `postpaid`. Pro postpago a 0 → «Pospago»,
   nunca `$0.02` inventado. Filas de retención hardcodeadas salen; celdas «—» o
   `description` / límites de la API.
4. **Confirmación web E9-04** en `/app/confirm` (alias `/app/confirmacion`): deep-link con
   `token`, `summary`, `expires_at`. POST/DELETE `/confirm/{token}`. Errores 404/410/409.
   Banda marigold, token mono, countdown `mm:ss`.
5. **Toasts** first-party 1.2 s (URI copiada, respaldo encolado, reintento encolado, errores
   de mutación). Sin dependencia nueva.
6. **Banner de cuenta suspendida** en el shell cuando `user.status === "suspended"`.
7. **Reintentar** en detalle (y/o dashboard) si `observed_state === "failed"` →
   `POST /ponds/{id}/retry`. **Respaldar ahora** en respaldos → `POST /ponds/{id}/backups`.
8. Columna **Expira** permanece; celdas «—» (no hay `expires_at` en `BackupOut`; sin cálculo
   de retención en el cliente ni edición de contrato).

Arquitectura de información: mockups pantallas 2, 5, 8, 11 y banner de suspensión.
Piel: `docs/visual-guidelines.md`.

## Entradas ya decididas (no se cambian)

- Solo `apps/web/**` y `docs/tickets/w2/**`. Sin `apps/api`, sin editar `schema.d.ts` /
  `openapi.json`, sin dependencias nuevas.
- Endpoints ya en OpenAPI: list/cancel subscriptions, confirm POST/DELETE, retry, trigger
  backup, plans, subscribe.
- Rama `w2-a2-web-gaps`. Ticket id **W2-15** (nunca W2-14 ni W1-27).
- Páginas ≤ 250 líneas (extraer si `backups-page` crece; ya está en 265).
- Autoría Carlos Hugo Escobar `<hescobar06cvo@gmail.com>`. Sin trailers de herramienta.
- No merge. Proof (375 + 1440) embebido en el cuerpo del PR, no en `media/`.

## Criterios de aceptación

1. `/app/billing` lista suscripciones del usuario con estados legibles y «Cancelar al corte»
   cuando aplica; tras cancelar, `cancel_at_period_end` se refleja (prueba + MSW).
2. Checkout exige el checkbox de pago simulado; sin él el submit está deshabilitado.
3. Ningún `$0.02` / `USD 0.02` hardcodeado en planes/landing; Pro postpago no se muestra como
   `$0` mensual inventado como tarifa horaria; retención «Diarios (7/30 días)» eliminada.
4. `/app/confirm?token&summary&expires_at` confirma y descarta; 404/410/409 muestran
   `problemToMessage` sin inventar campos `action` / «propuesto por».
5. Toasts de 1200 ms visibles tras copiar URI / encolar backup / encolar retry (y error).
6. Usuario `suspended` ve banner global marigold; usuario `active` no.
7. Pond `failed` muestra Reintentar y llama retry; respaldos tienen «Respaldar ahora».
8. Columna Expira sigue presente; celdas «—» sin inventar fechas.
9. `make check-web` verde. Checklist visual §11.2 marcado en el PR.
10. Un solo archivo de ticket en el PR. Diff neto ≤ 500 líneas o se parte en W2-16+.

## No tocar

- `apps/api/**`, `packages/contracts/**`, `schema.d.ts`, migraciones, stop/start pond,
  columnas size/last-error, admin totals, usage matrix, invoice history (A3 / A1).
- Ticket ids W2-14, W1-27.
- Dependencias nuevas no nombradas.

## Si algo falta

- Si hace falta `BackupOut.expires_at` o `billing_model`/`unit_price`/`backup_retention_days`:
  no inventar; dejar UI honesta («—» / «Pospago») y anotar en Decisiones del PR.
- `BLOQUEADO` solo si hay que *editar* contrato congelado.

## Referencia

- Issue #96 amendment r2 (A8, A9, A11 UI, retry/backup-now UI, checkbox, strip hardcodes).
- `docs/entrega-2/mockups/pantallas-principales.html` pantallas 2, 5, 8, 11 + banner suspensión.
- `docs/visual-guidelines.md` §6.2 banner, §6.5 confirm/toast.
- Store grounding: `internal/a2-wave/grounding.md`, `design-lock.md`.
