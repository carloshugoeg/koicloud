# Revisión SOLID — módulos del control plane

**Fecha:** 2026-10-22  
**Alcance:** código actual en `main` (`779efda`) · ítem P7 de [#96](https://github.com/carloshugoeg/koicloud/issues/96)  
**Método:** revisión estática por módulo (sin refactors en este PR). Criterios: SRP, OCP, LSP, ISP, DIP, alineados con `AGENTS.md` §4 y `.cursor/rules/10-api.mdc` (`router → service → models`).  
**Convención de estado:** `ok` · `menor` · `debe-ticket` (arreglo estimado >30 min → ticket en `docs/tickets/`).

---

## Resumen

| Módulo | Estado | Archivo principal | Ticket si >30 min |
|--------|--------|-------------------|-------------------|
| billing | ok (DIP G1) | `apps/api/app/modules/billing/service.py` | — |
| ponds | debe-ticket | `apps/api/app/modules/ponds/service.py` | [W1-21](../tickets/w1/W1-21-pond-service-srp.md) |
| jobs | debe-ticket | `apps/api/app/modules/jobs/service.py` | [W1-22](../tickets/w1/W1-22-job-transitions-ocp.md) |
| sql_console | menor | `apps/api/app/modules/sql_console/router.py` | [W1-23](../tickets/w1/W1-23-sql-history-dip.md) |
| metering | ok | `apps/api/app/modules/metering/service.py` | — |

---

## billing

**Estado:** `ok` (DIP de pago cumplido; G1 cerrado)  
**Archivos:** `apps/api/app/modules/billing/service.py`, `payments/port.py`, `payments/__init__.py`, `payments/simulated.py`, `invoice_pdf.py`

### G1 — `PaymentProvider` (DIP) — hecho

Decisión del 9 oct (#11 / G1). Verificación contra el código actual:

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| `BillingService` recibe `PaymentProvider` por inyección y no importa adaptadores | ✅ | `service.py` importa solo `payments.port`; ctor `(session, settings, payment_provider)` |
| Factory en `payments/__init__.py` + `PAYMENT_PROVIDER=simulated` | ✅ | `get_payment_provider(settings)` → `SimulatedPaymentProvider` |
| Mismo `confirm_payment()` para flujo síncrono y asíncrono | ✅ | `_start_and_maybe_confirm` llama `confirm_payment(provider_ref)` cuando el intento ya viene `SUCCEEDED` |
| Webhook `POST /billing/webhooks/{provider}` | ⬜ fuera de alcance (decisión) | — |

El comando `commands/billing.py` arma el servicio con `get_payment_provider(settings)`; el servicio de dominio no conoce `simulated`.

### Otros principios

- **SRP:** el servicio agrupa planes, suscripciones, facturas, pagos y PDF. Es ancho, pero el dominio de facturación académica es uno solo; no justifica un ticket solo por tamaño.
- **OCP:** un proveedor nuevo se añade en la factory + módulo bajo `payments/`, sin tocar `BillingService`.
- **LSP / ISP:** el `Protocol` `PaymentProvider` es mínimo (`start_payment`, `parse_confirmation`).
- **Olor menor (no ticket):** varios `AppError(ErrorCode.POND_NOT_FOUND)` para pago/factura/suscripción ausentes — catálogo, no estructura SOLID.

**Conclusión:** no hay refactor >30 min pendiente por SOLID en billing.

---

## ponds

**Estado:** `debe-ticket`  
**Archivo:** `apps/api/app/modules/ponds/service.py` (~392 líneas)

### Hallazgos

| Principio | Hallazgo | Severidad |
|-----------|----------|-----------|
| **SRP** | `PondService` mezcla CRUD de ponds, upsert de usuario (`ensure_actor`), auto-suscripción Micro (`ensure_subscription`), upsert/stale de nodo (`ensure_live_node` / `_upsert_node`), cuota, puertos, URI y orquestación de delete→backup | alto |
| **DIP** | Importa concreto `BackupService` dentro de `delete` | medio |
| **DRY / DIP** | `_upsert_node` diverge de `JobService._touch_node` (jobs siempre marca `ALIVE` + `last_seen_at`; ponds solo si `last_seen_at is None`) | medio |

Los comandos en `commands/ponds.py` delegan bien al servicio (capa fina). El problema está *dentro* del módulo.

**Ticket:** [W1-21](../tickets/w1/W1-21-pond-service-srp.md) — extraer actor/suscripción/nodo; un solo touch de nodo compartido con jobs.

---

## jobs

**Estado:** `debe-ticket`  
**Archivo:** `apps/api/app/modules/jobs/service.py` (~220 líneas)

### Hallazgos

| Principio | Hallazgo | Severidad |
|-----------|----------|-----------|
| **OCP** | `complete()` es una cadena `if/elif` por `JobType` (create/start/delete/backup/restore + fallos). Añadir un tipo de job obliga a editar este método | alto |
| **SRP** | El mismo método actualiza job, `PondStatus`, `Pond`, `Backup` y encola `DELETE_POND` tras `PRE_DELETE` | medio |
| **DRY** | `_touch_node` duplicado y semánticamente distinto al upsert de ponds (ver arriba) | medio |

`claim()` con `FOR UPDATE SKIP LOCKED` está bien acotado. Heartbeat + claim + complete es el rol natural del módulo; el olor es la tabla de transiciones implícita.

**Ticket:** [W1-22](../tickets/w1/W1-22-job-transitions-ocp.md) — tabla/función de transición explícita + unificar touch de nodo con ponds.

---

## sql_console

**Estado:** `menor` (con ticket para el cableado completo)  
**Archivos:** `apps/api/app/modules/sql_console/router.py`, `service.py`, `models.py`

### Observación (#96) — `AsyncSession` en el router

`sql_console/router.py` importa `AsyncSession` y, en `list_sql_history`, inyecta `get_session` y llama a `SqlConsoleService(session)` directamente. El router conoce la persistencia (DIP / capa HTTP).

Notas de contexto:

1. **`run_sql` en el mismo router sí delega** a `commands.sql.run_sql` sin sesión — patrón correcto.
2. **El router del módulo no está montado** en `main.py`. Producción usa `api_v1.py` → `commands.sql.list_sql_history`, que hoy devuelve `SQLHistoryResponse.example()` (fixture).
3. Las pruebas de `sql_console/tests/` montan el router del módulo a mano; ahí sí se ejercita la ruta con `AsyncSession`.

### Otros

- **SRP del service:** `SqlConsoleService` (historial truncado + paginación por cursor) está bien acotado.
- **ISP:** el router usa `HTTPException(422)` para cursor inválido en lugar de `AppError` del catálogo — olor menor de consistencia, no bloqueante.

**Ticket:** [W1-23](../tickets/w1/W1-23-sql-history-dip.md) — historial real vía `commands/sql.py` y routers sin `AsyncSession` (quitar la dependencia de persistencia en la capa HTTP). Estimado >30 min con pruebas.

---

## metering

**Estado:** `ok`  
**Archivo:** `apps/api/app/modules/metering/service.py`

### Hallazgos

| Principio | Evaluación |
|-----------|------------|
| **SRP** | Ingesta de muestras, agregación diaria e informe de uso mensual viven juntos en el dominio de medición; coherente |
| **OCP** | `compute_day_metrics` es función pura y testeable; la política de “ventana inicial = running” está documentada en el docstring |
| **DIP** | Depende de `AsyncSession` + modelos de `core` (patrón del monorepo); no hay adaptadores externos que abstraer |
| **ISP** | Superficie estrecha: ingest / aggregate_day / get_usage |

Dos caminos de ingesta (`ingest_samples` por id, `ingest_heartbeat_samples` por nombre) son adaptadores al contrato interno, no una violación. Sin ticket.

---

## Fuera de alcance de esta revisión

- Routers monolitos en `api_v1.py` / ownership W1 vs módulos (harness; no es un hallazgo nuevo de estos cinco módulos).
- Fixtures en `commands/*` que aún responden `example()` (p. ej. `run_sql` / `list_sql_history` en producción) — deuda de persistencia, citada solo donde afecta DIP de `sql_console`.
- Web, CLI, MCP, node-agent.

---

## Cómo usar este documento

1. Antes de un refactor de capas, leer la fila del módulo.
2. Si el arreglo cabe en <30 min y no toca contrato congelado, se puede hacer en un PR de higiene W1 sin ticket nuevo.
3. Si supera ~30 min o cruza ownership, abrir/usar el ticket enlazado; no mezclar con entregas de producto.

**PR de esta revisión:** [#101](https://github.com/carloshugoeg/koicloud/pull/101).
