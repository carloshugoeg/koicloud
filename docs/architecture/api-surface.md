# Superficie de API

Este documento fija:

1. El **contrato HTTP** del control plane (`/api/v1/*`, `/internal/v1/*`, `/mcp`).
2. El **patrón `propose → confirm`** para mutaciones desde CLI y MCP.
3. La **correspondencia CLI → API** y **MCP tool → API/commands**.
4. Los **códigos de error** que todos los clientes deben conocer.

Está diseñado para ser el borrador del OpenAPI generado por `apps/api`. La estructura del código real puede iterar; el contrato no cambia sin CCR (§9 de [`agent-docs.md`](./agent-docs.md)).

---

## 1. Convenciones transversales

- **Base URL:** `https://<KOICLOUD_DOMAIN>/api/v1`.
- **Auth Cliente/Admin:** `Authorization: Bearer <JWT>` (15 min). Refresh en `POST /auth/refresh` (30 días, rotativo).
- **Auth Node-agent:** `X-Node-Token: <secret>` sobre `/internal/v1/*` (Caddy limita a loopback).
- **Auth MCP (gate mínima):** `Basic <slug>:<password>` (o header `X-KOI-Agent-Password`) sobre `/mcp`.
- **Idempotency-Key:** header opcional en POST/DELETE — se guarda hash 24 h para descartar duplicados.
- **Content type:** `application/json` en request y response.
- **Fechas:** ISO-8601 UTC con `Z`.
- **Errores:** JSON con `code` del catálogo + `message` humano en español + `request_id`. Ejemplo:

  ```json
  {
    "code": "quota_exceeded",
    "message": "Ya alcanzaste el máximo de ponds (1) de tu plan.",
    "request_id": "req_01H…"
  }
  ```

- **Paginación:** cursor opaco (`?cursor=…&limit=50`); respuesta trae `next_cursor`.
- **Versionado:** `/v1` inmutable. Cambios rompedores exigirán `/v2` (no previsto en el semestre).

---

## 2. Catálogo de rutas `/api/v1/*`

Notación: `M ROUTE → CommandOrService` con response resumido. `[C]` = requiere confirm cuando se llama desde CLI/MCP.

### 2.1 Auth y usuarios

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| POST | `/auth/register` | `register_user` | Alta con email + pass + full_name + nit? | `{user_id, email_verified:false}` |
| POST | `/auth/verify` | `verify_email` | Consume token de verificación. Body JSON `VerifyEmailRequest` `{token}` (no query) | `{user_id, email_verified:true}` |
| POST | `/auth/login` | `issue_tokens` | Login → JWT + refresh | `{access_token, refresh_token, user}` |
| POST | `/auth/refresh` | `rotate_refresh` | Rota refresh y emite JWT | `{access_token, refresh_token}` |
| POST | `/auth/forgot` | `send_reset_token` | Envía email de reset | `{ok:true}` |
| POST | `/auth/reset` | `reset_password` | Consume token + nueva contraseña | `{ok:true}` |
| POST | `/auth/logout` | `revoke_refresh` | Revoca refresh actual | `204` |
| GET | `/me` | `get_me` | Perfil del usuario logueado | `{user, subscription?, ponds_count}` |
| PATCH | `/me` | `update_profile` | Actualiza `full_name`, `nit` | `{user}` |

### 2.2 Planes y suscripciones

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| GET | `/plans` | `list_plans` | Catálogo público | `[{plan}]` |
| GET | `/subscriptions` | `list_my_subscriptions` | Historial del usuario | `[{subscription}]` |
| POST | `/subscriptions` | `subscribe` [C-CLI/MCP] | Contrata plan; genera invoice + payment simulado | `{subscription, invoice, payment}` |
| POST | `/subscriptions/{id}/cancel` | `cancel_subscription` [C-CLI/MCP] | Cancela al fin del período | `{subscription}` |
| GET | `/invoices` | `list_invoices` | Historial | `[{invoice}]` |
| GET | `/invoices/{id}` | `get_invoice` | Detalle con líneas | `{invoice, lines[]}` |
| GET | `/invoices/{id}/pdf` | `get_invoice_pdf` | Descarga | `application/pdf` |

### 2.3 Ponds

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| GET | `/ponds` | `list_ponds` | Lista del usuario | `[{pond}]` |
| POST | `/ponds` | `create_pond` [C-CLI/MCP] | Crea (nombre, plan heredado, versión=16) | `202 {pond, job}` |
| GET | `/ponds/{id}` | `get_pond` | Detalle con estado observado | `{pond}` |
| GET | `/ponds/by-name/{name}` | `get_pond_by_name` | Lookup por nombre | `{pond}` |
| GET | `/ponds/{id}/connection` | `get_connection` | Host/port/user/pass/uri | `{connection}` |
| POST | `/ponds/{id}/retry` | `retry_failed_job` [C-CLI/MCP] | Reencola último job failed | `202 {job}` |
| DELETE | `/ponds/{id}` | `delete_pond` [C-CLI/MCP] | Encola backup pre_delete + delete | `202 {pond, jobs[]}` |

### 2.4 Respaldos

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| GET | `/ponds/{id}/backups` | `list_backups` | Lista respaldos del pond | `[{backup}]` |
| POST | `/ponds/{id}/backups` | `trigger_backup` [C-CLI/MCP] | Encola backup on-demand | `202 {backup, job}` |
| POST | `/ponds/{id}/restore` | `restore_backup` [C-CLI/MCP] | Encola restore con `{backup_id}` | `202 {job}` |

### 2.5 Consola SQL

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| POST | `/ponds/{id}/sql` | `run_sql` | Ejecuta query; body `{query, mode:read|write}` — modo `write` desde CLI/MCP requiere confirmación previa | `{columns, rows[≤1000], row_count, duration_ms, truncated}` |
| GET | `/ponds/{id}/sql/history` | `list_sql_history` | Últimas consultas del usuario en ese pond | `[{sql_event}]` |

### 2.6 Uso

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| GET | `/usage` | `get_usage` | Query `?month=YYYY-MM` (default: mes actual) | `{month, total_instance_hours, total_storage_gb_hours, ponds:[{pond_id, instance_hours, storage_gb_hours}]}` |

### 2.7 Acceso agente (gate mínima)

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| GET | `/agent-access` | `get_agent_access` | Slug + `enabled` (no muestra password) | `{slug, url, enabled, rotated_at}` |
| POST | `/agent-access/rotate` | `rotate_agent_password` [C-CLI] | Genera nueva password (única vez visible) | `{slug, url, password}` |
| POST | `/agent-access/toggle` | `toggle_agent_access` [C-CLI] | Activa/desactiva | `{enabled}` |

### 2.8 Confirmaciones (usadas por CLI/MCP)

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| POST | `/confirm/{token}` | `confirm_action` | Consume token; ejecuta el comando pendiente | Respuesta del comando efectivo (p. ej. `202 {pond}` si era `create_pond`) |
| DELETE | `/confirm/{token}` | `discard_pending_confirmation` | El usuario descarta la propuesta | `204` |

### 2.9 Administración

Todas requieren `role=admin`.

| M | Ruta | Command | Descripción | Response |
|---|------|---------|-------------|----------|
| GET | `/admin/users` | `admin_list_users` | Paginado | `[{admin_user}]` |
| POST | `/admin/users/{id}/suspend` | `suspend_user` (siempre requiere confirm textual del admin en Web) | Suspende | `{user}` |
| POST | `/admin/users/{id}/reactivate` | `reactivate_user` | Reactiva | `{user}` |
| GET | `/admin/ponds` | `admin_list_ponds` | Todos los ponds; filtros | `[{admin_pond}]` |
| GET | `/admin/audit` | `admin_list_audit` | Últimos eventos sensibles | `[{event}]` |

### 2.10 Health

| M | Ruta | Descripción | Response |
|---|------|-------------|----------|
| GET | `/health` | Liveness (`{ok:true, git_sha}`) | 200 |
| GET | `/ready` | Readiness (base viva, agente heartbeat < 60 s) | 200 o 503 |

---

## 3. Rutas internas `/internal/v1/*`

Solo el node-agent las llama. `X-Node-Token` obligatorio; Caddy bloquea si origen no es `127.0.0.1`.

| M | Ruta | Descripción | Body / Response |
|---|------|-------------|-----------------|
| POST | `/internal/v1/heartbeat` | Estado del nodo + contenedores + samples | `{containers:[{name, state, uptime}], samples:[{pond_name, size_bytes}]}` → `{ok:true}` |
| POST | `/internal/v1/jobs/claim` | Reclama un job pendiente | `{max_types:[…]}` opcional → `{job}` o `204` |
| POST | `/internal/v1/jobs/{id}/complete` | Reporta resultado | `{status: succeeded|failed, result?, error?}` → `204` |
| POST | `/internal/v1/samples` | Muestreo puntual fuera de heartbeat (opcional) | `[{pond_id, size_bytes, container_state}]` → `{ok:true}` |

`payload` de un job (respuesta a claim):

```json
{
  "id": "…",
  "type": "create_pond",
  "pond_id": "…",
  "payload": {
    "name": "koi-pond-a1b2",
    "host_port": 15007,
    "memory_mb": 512,
    "cpus": 0.5,
    "db_password_plain": "<Fernet-decrypted>",
    "image": "postgres:16-alpine"
  }
}
```

---

## 4. Superficie MCP (`/mcp`)

Servidor **FastMCP** montado en el mismo proceso API. Cada tool es de ≤ 25 líneas y delega en `commands/*` o en `commands.propose_action` / `commands.confirm_action`.

| Tool | Descripción | Read-only | Mutación (usa propose) |
|------|-------------|-----------|-----------------------|
| `whoami()` | Devuelve el usuario dueño de la sesión MCP | ✓ | — |
| `list_ponds()` | Lista ponds del usuario | ✓ | — |
| `get_pond(name)` | Detalle de un pond | ✓ | — |
| `get_connection(name)` | URI y credenciales del pond | ✓ | — |
| `create_pond(name)` | Encola creación | — | ✓ |
| `delete_pond(name)` | Encola eliminación con backup previo | — | ✓ |
| `list_subscriptions()` | Suscripciones del usuario | ✓ | — |
| `list_backups(pond_name)` | Respaldos disponibles | ✓ | — |
| `restore_backup(pond_name, backup_id)` | Encola restore | — | ✓ |
| `run_sql(pond_name, query, mode)` | Ejecuta SQL — `mode="read"` directo; `mode="write"` con propose | Depende | Sí para `write` |
| `get_usage(month?)` | Uso del mes | ✓ | — |
| `confirm_action(token)` | Consume un `pending_confirmations` | — | Ejecuta el pendiente |
| `cancel_confirmation(token)` | Descarta un token propuesto | — | Descarta |

**Respuesta de tool mutante (primer paso):**

```json
{
  "status": "confirmation_required",
  "token": "conf_…",
  "summary": "Se eliminará el pond 'inventario-mvp'. Se creará un respaldo previo automático. Expira en 5 min."
}
```

**Prompt sistema del server MCP** (documental; se implementa en `apps/api/app/mcp/prompt.py`):

> Sos un asistente que opera KoiCloud (DBaaS académico). Antes de invocar una tool mutante, explicá al humano qué vas a hacer y esperá su OK. Cuando la API devuelva `confirmation_required`, mostrá el `summary` textual y pedí confirmación explícita al humano. Solo entonces invocá `confirm_action(token=…)`. Para tools con `read_only=true` no hace falta confirmación. Nunca inventes tokens ni cambies el `summary`.

---

## 5. Superficie CLI (`koicloud`)

| Comando | API llamada | Notas |
|---------|-------------|-------|
| `koicloud login` | `POST /auth/login` | Guarda tokens en `~/.config/koicloud/config.json` |
| `koicloud logout` | `POST /auth/logout` | Borra config |
| `koicloud whoami` | `GET /me` | — |
| `koicloud plan list` | `GET /plans` | Tabla |
| `koicloud subscription list` | `GET /subscriptions` | — |
| `koicloud subscription subscribe <plan_id>` | `POST /subscriptions` (con confirm) | Doble confirm |
| `koicloud subscription cancel <sub_id>` | `POST /subscriptions/{id}/cancel` (con confirm) | Doble confirm |
| `koicloud pond list` | `GET /ponds` | Tabla |
| `koicloud pond get <name>` | `GET /ponds/by-name/{name}` | — |
| `koicloud pond create <name>` | `POST /ponds` (con confirm) | Doble confirm |
| `koicloud pond connection <name>` | `GET /ponds/{id}/connection` | Imprime URI copiable |
| `koicloud pond delete <name>` | `DELETE /ponds/{id}` (con confirm) | Doble confirm |
| `koicloud sql run --pond <name> -q "…"` | `POST /ponds/{id}/sql {mode:read}` | Modo read por defecto |
| `koicloud sql run --pond <name> -q "…" --write` | `POST /ponds/{id}/sql {mode:write}` (con confirm) | Doble confirm |
| `koicloud sql history --pond <name>` | `GET /ponds/{id}/sql/history` | — |
| `koicloud backup list --pond <name>` | `GET /ponds/{id}/backups` | — |
| `koicloud backup restore --pond <name> --backup <id>` | `POST /ponds/{id}/restore` (con confirm) | Doble confirm |
| `koicloud agent show` | `GET /agent-access` | Imprime slug + URL (no password) |
| `koicloud agent rotate` | `POST /agent-access/rotate` (con confirm) | Muestra la nueva password una sola vez |
| `koicloud usage` | `GET /usage` | Vista tabular |
| `koicloud confirm <token>` | `POST /confirm/{token}` | Genérico para cualquier pendiente |
| `koicloud confirm cancel <token>` | `DELETE /confirm/{token}` | Descarta pendiente |

**Convenciones CLI:**

- `--yes <token>` (opcional): permite pasar el token directo, útil para scripts CI.
- `-o json` para todas las salidas (útil en CI). Default: tablas humanas con `rich`.
- Cuando el usuario no está logueado, cualquier comando devuelve `1` con “Primero corré `koicloud login`”. Valor congelado: **`1`** (el `2` de la matriz de inputs no aplica).

---

## 6. Patrón `propose → confirm token` (contrato canónico)

### 6.1 Diseño

El objetivo es: **cualquier mutación desde un canal no navegador exige dos pasos separados en el tiempo**, con un resumen humano visible en medio. La Web puede saltearlo porque el usuario ya está en la sesión interactiva; la CLI y el MCP lo requieren siempre.

### 6.2 Detección server-side

La misma ruta HTTP soporta los dos modos:

- Si el request viene con `X-KOI-Confirm-Token: <token>`, la API busca el token en `pending_confirmations`, valida que corresponda a la misma ruta + payload y ejecuta.
- Si viene sin token **y** el request es mutante **y** la superficie es CLI o MCP (detectado por header `X-KOI-Surface: cli|mcp` o por el hecho de que la request llegó via `/mcp`), la API crea el `pending_confirmations` y responde `409 confirmation_required`.

Es decir, el mismo endpoint (`DELETE /ponds/{id}`) puede responder:

- `202 Accepted` (con token en el header): ejecuta.
- `202 Accepted` (sin token, superficie web): ejecuta.
- `409 confirmation_required` (sin token, superficie CLI/MCP): devuelve token.

### 6.3 Respuesta canónica de `409 confirmation_required`

```json
{
  "status": "confirmation_required",
  "token": "conf_…",
  "summary": "Se eliminará el pond 'inventario-mvp'. Se creará un respaldo previo automático. Expira en 5 min.",
  "expires_at": "2026-09-14T20:00:00Z",
  "next": {
    "confirm_url": "/api/v1/confirm/conf_…",
    "cli_example": "koicloud confirm conf_…"
  }
}
```

### 6.4 Consumo del token

```
POST /api/v1/confirm/{token}
```

Sin body (todo lo necesario vive en `pending_confirmations.payload`). La API:

1. `SELECT … WHERE token_hash = SHA256(token) AND consumed_at IS NULL AND expires_at > now() FOR UPDATE`.
2. Si falta, `410 confirmation_expired` o `404 confirmation_not_found`.
3. Si existe, `UPDATE consumed_at = now()` y despacha al comando original con el `payload`.
4. Devuelve la misma respuesta que hubiera devuelto la mutación (`202 {pond}`, etc.).

### 6.5 Expiración y limpieza

- TTL default: **5 minutos**. Configurable por env (`CONFIRM_TTL_SECONDS`).
- Cron diario elimina `pending_confirmations` con `expires_at < now() - 24h`.

### 6.6 Idempotency-Key

Ortogonal al confirm. Si el mismo `Idempotency-Key` llega dos veces en 24 h con el mismo request, el segundo devuelve la misma respuesta cacheada. Útil para prevenir doble creación en clientes con retry.

---

## 7. Catálogo de códigos de error

Códigos estables (fuente única para clientes). El backend lanza `AppError(code=…, message=…, http_status=…)`.

| Code | HTTP | Contexto | Mensaje típico |
|------|------|----------|----------------|
| `invalid_credentials` | 401 | login | “Correo o contraseña incorrectos” |
| `email_not_verified` | 403 | login | “Verificá tu correo antes de continuar” |
| `account_suspended` | 403 | login o cualquier | “Cuenta suspendida por el administrador” |
| `token_expired` | 401 | JWT | “Sesión expirada, iniciá sesión otra vez” |
| `token_invalid` | 401 | JWT / email / reset | — |
| `email_taken` | 409 | register | “Ese correo ya está registrado” |
| `password_too_weak` | 422 | register / reset | — |
| `plan_required` | 409 | create_pond, restore | “Necesitás una suscripción activa” |
| `quota_exceeded` | 409 | create_pond | “Alcanzaste el máximo de ponds del plan” |
| `pond_name_taken` | 409 | create_pond | — |
| `pond_not_found` | 404 | ponds/{id}/… | — |
| `pond_busy` | 409 | mutación con job activo | — |
| `node_unavailable` | 503 | create_pond | — |
| `sql_readonly_violation` | 400 | run_sql | “La query es de escritura pero el modo es read” |
| `sql_timeout` | 504 | run_sql | “La consulta excedió 10 s” |
| `confirmation_required` | 409 | CLI/MCP mutación | — |
| `confirmation_not_found` | 404 | confirm | — |
| `confirmation_expired` | 410 | confirm | — |
| `confirmation_action_mismatch` | 409 | confirm | “El token no corresponde a esta acción” |
| `agent_disabled` | 403 | /mcp | “El acceso agente está desactivado” |
| `agent_bad_credentials` | 401 | /mcp | — |
| `not_owner` | 403 | cualquier recurso ajeno | — |
| `admin_only` | 403 | rutas admin | — |
| `rate_limited` | 429 | login/register/forgot/mcp | “Muchos intentos, esperá un momento” |
| `disk_full` | 507 | create_pond / backup | — |
| `internal_error` | 500 | genérico | “Algo salió mal, revisá los logs” |

**Nunca** un cliente hace switch por el `message`; siempre por el `code`. `message` se puede internacionalizar/refactorizar libremente.

---

## 8. Ejemplos completos de request / response

### 8.1 Crear pond desde Web

```
POST /api/v1/ponds
Authorization: Bearer eyJ…
Idempotency-Key: web-abc123

{ "name": "inventario-demo" }
```

```
202 Accepted
Content-Type: application/json

{
  "pond": {
    "id": "8f2c…",
    "name": "inventario-demo",
    "engine_version": "16",
    "desired_state": "running",
    "observed_state": "pending"
  },
  "job": { "id": "j-1e…", "type": "create_pond", "status": "queued" }
}
```

### 8.2 Eliminar pond desde CLI (propose)

```
DELETE /api/v1/ponds/8f2c…
Authorization: Bearer eyJ…
X-KOI-Surface: cli
```

```
409 Conflict

{
  "status": "confirmation_required",
  "token": "conf_r7…",
  "summary": "Se eliminará el pond 'inventario-demo'. Se creará un respaldo previo automático. Expira en 5 min.",
  "expires_at": "2026-09-14T20:05:00Z",
  "next": {
    "confirm_url": "/api/v1/confirm/conf_r7…",
    "cli_example": "koicloud confirm conf_r7…"
  }
}
```

### 8.3 Confirmar

```
POST /api/v1/confirm/conf_r7…
Authorization: Bearer eyJ…
```

```
202 Accepted

{
  "pond": { "id": "8f2c…", "desired_state": "deleted", "observed_state": "deleting" },
  "jobs": [
    { "id": "j-2b…", "type": "backup_pond", "kind": "pre_delete", "status": "queued" },
    { "id": "j-2c…", "type": "delete_pond", "status": "queued" }
  ]
}
```

### 8.4 SQL read desde MCP

Tool call `run_sql(pond_name="inventario-demo", query="SELECT 1", mode="read")` → llamada interna → API:

```
POST /api/v1/ponds/8f2c…/sql
Authorization: Bearer <token del agente=user via gate>
{ "query": "SELECT 1", "mode": "read" }
```

```
200 OK

{
  "columns": ["?column?"],
  "rows": [[1]],
  "row_count": 1,
  "duration_ms": 4,
  "truncated": false
}
```

---

## 9. Reglas de autorización por recurso

- **`/ponds/{id}`** y todos sus subpaths: solo el dueño (`ponds.user_id == ctx.user_id`) o rol admin sobre rutas `/admin/…`.
- **`/subscriptions/{id}`**, `/invoices/{id}`, `/agent-access`, `/usage`: solo dueño.
- **`/admin/*`**: solo rol admin.
- **`/mcp`**: ejecuta como el dueño del `agent_access` slug validado por password. Todo request MCP se traduce a un `user_id`; los objetos accesibles son los mismos que la Web para ese usuario.
- **`/internal/*`**: solo con `X-Node-Token` que hashee a un `nodes.token_hash` `alive`.

**Rate limits (slowapi):**

| Ruta | Límite por IP |
|------|----------------|
| `POST /auth/login` | 10/min |
| `POST /auth/register` | 5/min |
| `POST /auth/forgot` | 3/min |
| `/mcp` | 60/min por slug |
| `POST /confirm/{token}` | 20/min por usuario |
| `POST /ponds/{id}/sql` (write) | 10/min por usuario |

---

## 10. Reglas de contrato para agentes

- Cada endpoint se implementa con `schemas.py` (Pydantic v2) con `example` en `json_schema_extra`. El frontend arma sus mocks MSW con esos `example`.
- Cada endpoint tiene una prueba de API (`tests/test_api.py`) que valida caso feliz + al menos un error del catálogo.
- Cambios de contrato solo por CCR; el PR de contrato regenera `packages/contracts/openapi.json` y `apps/web/src/api/schema.d.ts`, y agrega línea a `packages/contracts/CHANGELOG.md`.
- Añadir un campo opcional en la respuesta también es un cambio de contrato (regenera el cliente TS). Se resuelve como CCR exprés.
- **Nunca** se agrega un endpoint nuevo “de conveniencia”. Si el frontend necesita datos, se compone con endpoints existentes o se pide CCR.

---

## 11. Qué NO existe en esta superficie (y por qué)

- **`/organizations`, `/teams`**: sin organizaciones; usuario individual.
- **`/api-keys`, `/agent-keys`**: sin API keys con scopes; solo `agent_access` con URL+password.
- **`/approvals`**: sin workflow de aprobación humano-a-bot; el `pending_confirmations` es el usuario aprobando a sí mismo.
- **`/status`**: sin status page pública.
- **`/webhooks`**: sin webhooks salientes.
- **`/oauth/*`**: sin OAuth 2.1.

Cualquiera de estas se rechaza como scope creep sin CCR previo.
