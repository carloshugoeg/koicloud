# Revisión SOLID — módulos principales del control plane

**Fecha:** 2026-11-10  
**Alcance:** `main` actual + refactors de este PR (`w1-solid-review` / W1-50)  
**Módulos:** auth · billing/payments · ponds/provisioning · metering · MCP/agent access · admin  
**Método:** revisión estática con citas `ruta:línea` verificadas en el árbol. Criterios S·O·L·I·D alineados con `AGENTS.md` §4.  
**Convención:** cada principio trae un ejemplo **cumplido** y, si aplica, una **violación**. Los arreglos hechos aquí listan antes → después.

---

## Resumen

| Módulo | Lectura rápida | Refactor en este PR |
|--------|----------------|---------------------|
| auth | Bien separado servicio→comandos; token de nodo ahora en tiempo constante | `node_token_matches` |
| billing/payments | DIP de `PaymentProvider` sólido | — |
| ponds | SRP ancho + DIP a `BackupService` concreto | recomendación (W1-21; no tocar aquí por PR #236) |
| metering | Funciones puras + servicio de dominio acotado | — |
| MCP / agent access | Tools delgadas; gate partido en autenticadores | split de `authenticate_mcp` |
| admin | Usuarios vía commands; listados abren `SessionLocal` | recomendación |

---

## Refactors aplicados (comportamiento igual)

### R1 — Comparación en tiempo constante del token de nodo

- **Antes:** `apps/api/app/core/auth.py` usaba `x_node_token != settings.node_token` (comparación corta ante fallo).
- **Después:** `node_token_matches` en `apps/api/app/core/auth.py:22` con `hmac.compare_digest`; `get_node_identity` en `:98` llama `:102`.
- **Pruebas:** `apps/api/tests/test_node_token_compare.py`.

### R2 — Gate MCP: un autenticador por tipo de credencial

- **Antes:** `authenticate_mcp` mezclaba parseo, bootstrap demo, pond-token y agent-access en un solo cuerpo (~50 líneas).
- **Después:** `_authenticate_pond_token` (`apps/api/app/mcp/gate.py:78`), `_authenticate_agent_access` (`:97`), `_actor_from_user` (`:33`); `authenticate_mcp` (`:110`) solo orquesta.
- **Pruebas:** suite MCP existente (`tests/test_mcp_gate_confirm.py`, `app/mcp/tests`).

---

## auth

**Archivos:** `apps/api/app/modules/auth/service.py`, `apps/api/app/core/auth.py`, `apps/api/app/core/security.py`

| Principio | Cumple | Violación / nota |
|-----------|--------|------------------|
| **S** | `AuthService` solo delega a `app.commands.auth` (`service.py:25`, p. ej. `register_user` en `:31`) | `logout` (`:55`) concentra cookie + revoke refresh + revoke access; aceptable como un caso de uso |
| **O** | Nuevos flujos de auth se añaden como métodos delgados que llaman un comando nuevo, sin reabrir el router | ninguna relevante |
| **L** | `get_admin_user` (`core/auth.py:90`) reusa `get_current_user` y solo endurece el rol | ninguna |
| **I** | Dependencias HTTP (`HTTPBearer`, headers) viven en `core/auth.py`; el servicio de módulo no importa FastAPI | ninguna |
| **D** | Hash/verify de password detrás de `core/security.py:24` (`verify_password`) | **corregida:** el token de nodo ya no usa `!=` (ver R1) |

---

## billing / payments

**Archivos:** `apps/api/app/modules/billing/service.py`, `payments/port.py`, `payments/__init__.py`, `payments/simulated.py`

| Principio | Cumple | Violación / nota |
|-----------|--------|------------------|
| **S** | Cobro, planes y PDF viven en el dominio de facturación; el puerto de pago está aparte (`payments/`) | `subscribe` (`service.py:151`, ~73 líneas) es largo; partirlo es mejora de lectura, no bloquea el curso |
| **O** | Un proveedor nuevo: entrada en `get_payment_provider` (`payments/__init__.py:8`) + módulo bajo `payments/`, sin editar reglas de `BillingService` | solo `simulated` hoy (`:11`) |
| **L** | `SimulatedPaymentProvider` (`payments/simulated.py:12`) cumple el `Protocol` `PaymentProvider` (`port.py:19`) | ninguna |
| **I** | El protocolo expone solo `start_payment` y `parse_confirmation` (`port.py:19`) | ninguna |
| **D** | `BillingService.__init__` recibe `PaymentProvider` (`service.py:100`–`:104`); no importa `simulated` | ninguna |

---

## ponds / provisioning

**Archivos:** `apps/api/app/modules/ponds/service.py`, `apps/api/app/commands/ponds.py`

| Principio | Cumple | Violación / nota |
|-----------|--------|------------------|
| **S** | Comandos en `commands/ponds.py` solo orquestan (`:31` y vecinos) | **violación:** `PondService` (`service.py:88`) mezcla create/stop/start/delete, `ensure_actor` (`:325`), `ensure_subscription` (`:354`) y `ensure_live_node` (`:343`) |
| **O** | Nuevos verbos de ciclo de vida se añaden como métodos + `JobType`; la cola no cambia | create (`:141`) sigue siendo un método grande |
| **L** | `pond_to_out` / `job_to_out` proyectan el mismo contrato hacia la API | ninguna |
| **I** | La superficie pública que usan los commands es la del servicio; no hay fat interface HTTP aquí | ninguna |
| **D** | Session + `Settings` inyectados en el constructor | **violación:** `delete` importa y instancia `BackupService` concreto (`service.py:198`–`:210`) |

**Recomendación (no en este PR):** ticket [W1-21](../tickets/w1/W1-21-pond-service-srp.md). No se refactoriza aquí para no chocar con el PR #236 (`ponds/service.py`).

---

## metering

**Archivos:** `apps/api/app/modules/metering/service.py`, `rates.py`, `samples.py`

| Principio | Cumple | Violación / nota |
|-----------|--------|------------------|
| **S** | `compute_day_metrics` es pura (`service.py:48`); persistencia en `MeteringService` (`:103`) | `get_usage` (`:205`) combina ventana mensual + filas; sigue siendo el caso de uso de “usage” |
| **O** | Tasas Pro salen de `rates.pro_hourly_unit_price_usd` (`rates.py`) reexportando el catálogo de billing | ninguna |
| **L** | Muestras node vs heartbeat son adaptadores al mismo agregado diario | ninguna |
| **I** | API estrecha: ingest / aggregate_day / get_usage (`:108`, `:152`, `:205`) | ninguna |
| **D** | Depende de `AsyncSession` + modelos (patrón del monorepo); sin proveedor externo que abstraer | ninguna |

---

## MCP / agent access

**Archivos:** `apps/api/app/mcp/gate.py`, `server.py`, `tools/*`, `apps/api/app/modules/agent_access/service.py`

| Principio | Cumple | Violación / nota |
|-----------|--------|------------------|
| **S** | Tools de lectura ≤ ~15 líneas y delegan a commands (p. ej. `tools/get_usage.py:10`) | **corregida en parte:** el gate ya no mezcla los dos caminos de auth (ver R2) |
| **O** | Tool nueva = archivo bajo `tools/` + registro FastMCP; el gate no se toca | ninguna |
| **L** | Credencial de agente y temp-link pond-* producen el mismo `AuthContext` vía `_actor_from_user` (`gate.py:33`) | ninguna |
| **I** | `AgentAccessService` (`service.py:30`) expone ensure/rotate/toggle/authenticate; el gate solo usa authenticate | ninguna |
| **D** | Gate depende de `AgentAccessService` / `PondTokenService`, no de SQL crudo; password vía `verify_password` (`agent_access/service.py:13`, uso en `:106`) | `authenticate_mcp` aún abre `SessionLocal` (aceptable como borde HTTP) |

---

## admin

**Archivos:** `apps/api/app/modules/admin/service.py`, `apps/api/app/commands/admin.py`

| Principio | Cumple | Violación / nota |
|-----------|--------|------------------|
| **S** | Acciones de usuario (`list_users` / suspend) delegan a commands (`service.py:39`) | Listados de ponds/subscriptions/totals/audit (`:55`+) concentran SQL de reporting |
| **O** | Filtro de bitácora sensible es una tupla (`SENSITIVE_AUDIT_ACTIONS`, `:28`) fácil de extender | ninguna fuerte |
| **L** | Respuestas tipadas (`AdminPondOut`, etc.) estables para la Web | ninguna |
| **I** | Métodos estáticos por operación; el router no ve SQL | ninguna |
| **D** | `list_users` → commands | **violación menor:** `list_ponds` abre `SessionLocal` directo (`:56`) mientras `commands/admin.py:195` vuelve a llamar al servicio (ciclo commands↔service) |

**Recomendación:** unificar listados admin detrás de commands con una sola dirección de dependencia (sin cambiar contratos HTTP).

---

## Fuera de alcance de esta pasada

- Jobs / sql_console (ya cubiertos en la revisión W1-24 / PRs asociados).
- Web, CLI, node-agent.
- Partir `PondService` o cablear un puerto `BackupEnqueue` (W1-21; evita conflicto con #236).
- Cambiar OpenAPI, firmas de `commands/*`, migraciones o env.

---

## Cómo usar este documento

1. El ingeniero del curso puede puntuar cada módulo con la tabla S·O·L·I·D y las citas.
2. Arreglos <30 min y sin contrato congelado caben en un PR de higiene W1 (como R1/R2).
3. Arreglos mayores → ticket enlazado; no mezclar con demos de producto.

**Ticket:** W1-50 · **Rama:** `w1-solid-review`.
