---
id: W2-15
workstream: W2
persona: Jason
estado: en-curso
rama: w2-suscripcion-historial
epica: "E2-05, E2-06"
sprint: S5
pr:
depends_on:
issue: "https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6428918452"
---

# [W2-15] Historial de suscripciones y cancelar al corte

## Qué se ve

Pantalla `/app/billing` (Facturación) con el historial de suscripciones del usuario
autenticado, badges de estado con glifo + texto, y la acción «Cancelar al corte»
para una suscripción `active` sin `cancel_at_period_end`. Tras confirmar en el
diálogo, la fila muestra que se cancelará al fin del período.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/billing` (ya registrada; hoy reexporta Uso).
- API: `GET /api/v1/subscriptions` y `POST /api/v1/subscriptions/{subscription_id}/cancel`.
- Campos de `SubscriptionOut`: `id`, `user_id`, `plan_id`, `status`,
  `current_period_start`, `current_period_end`, `cancel_at_period_end`.
- Sin `invoice_id` en la suscripción; no inventar columna de factura.
- Superficie web ejecuta el cancel directo (202); no usa `X-KOI-Confirm-Token`
  (eso es CLI/MCP y ticket A9).
- Cancel solo marca `cancel_at_period_end`; el `status` sigue `active` hasta el
  worker de renovación.
- Piel: `docs/visual-guidelines.md`; mockup IA en
  `docs/entrega-2/mockups/pantallas-principales.html` (tabla Plan · Estado ·
  Período · Acción).
- Issue #96 amendment A8 (LOW). Sin endpoints de dinero nuevos.

## Criterios de aceptación

1. `/app/billing` lista las suscripciones del usuario con plan, estado (glifo +
   texto), período y acción; `/app/uso` sigue siendo uso + facturas.
2. Estados de listado: cargando, vacío y error.
3. Una fila `active` sin cancel programado muestra «Cancelar al corte»; el
   diálogo resume plan y `current_period_end` antes del POST.
4. Tras cancelar con éxito, la UI refleja `cancel_at_period_end` (p. ej. «Se
   cancela al corte») sin fingir un `status` distinto.
5. Prueba de render + interacción: listado poblado, cancel feliz, y al menos un
   estado vacío o de error.
6. Checklist visual §11.2; usable a 360 px; sin koi sobre la tabla.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` salvo el `element`/`handle` ya cableado a billing.
- `src/components/ui/*` salvo tema si el ticket lo permite.
- Cualquier archivo fuera de `apps/web/` y `docs/tickets/w2/**`.
- OpenAPI, comandos, módulos de billing en API, migraciones.
- `docs/tickets/w2/W2-14-screen-map-fixes.md` (pertenece a PR #122).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, hooks, rutas ni códigos de error.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo
estilo de pruebas y misma forma de cerrar criterios en el PR. Amendment A8 en
issue #96. **ID correcto: W2-15** (W2-14 es screen-map en PR #122).
