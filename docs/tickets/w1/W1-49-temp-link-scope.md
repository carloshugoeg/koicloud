---
id: W1-49
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-temp-link-scope
epica: E9-02
sprint: S8
pr: https://github.com/carloshugoeg/koicloud/pull/236

depends_on:
---

# [W1-49] P0: el link temporal no sale del pond emitido

## Qué se ve

Un miembro de la audiencia con el link+password temporal (S2) solo puede usar el
pond para el que se emitió. No lista ni lee otros ponds. No entra a `/me`,
suscripciones, admin ni refresh. No llama `list_tables` ni otras tools fuera de
`TEMP_ACCESS_SCOPES`. Un token vencido o revocado deja de autenticar en MCP.

## Entradas ya decididas (no se cambian)

- `TEMP_ACCESS_SCOPES` = `whoami` / `get_pond` / `run_sql` en `apps/api/app/schemas.py`
  (`list_tables` queda fuera).
- Credencial = fila `pond_tokens` + Basic `slug:password` en `/mcp`
  (`PondTokenService.authenticate` → `AuthContext.pond_id` / `allowed_tools` /
  `pond_token_id`).
- Statechart: `docs/architecture/statecharts/pond-temp-access/`.
- Sin migración nueva. Sin CCR de OpenAPI.

## Criterios de aceptación

1. `test_streamable_list_tables_denied_as_agent_disabled`. Streamable HTTP
   `tools/call` de `list_tables` con Basic temporal responde `agent_disabled`
   (código HTTP 403 con `code`, o el mensaje de catálogo en el error del tool).
   No responde `node_unavailable` ni «No hay nodos disponibles en este momento».
2. `test_jsonrpc_out_of_allowlist_tools_return_agent_disabled`. JSON-RPC niega
   `list_tables`, `list_ponds`, `get_usage` y `list_subscriptions` con
   `403 agent_disabled`.
3. `test_cross_pond_get_pond_denied`. `get_pond` del pond emitido devuelve ese
   pond. `get_pond` de un segundo pond del mismo dueño, insertado por SQL,
   responde `pond_not_found` y no devuelve el otro pond.
4. `test_temp_basic_rejected_on_non_pond_http_routes`. Un `TestClient` sin
   cookies de login, con Basic temporal, recibe `401 token_invalid` en
   `GET /api/v1/me`, `GET /api/v1/ponds`, `GET /api/v1/ponds/{id}`,
   `GET /api/v1/subscriptions`, `GET /api/v1/admin/users`,
   `POST /api/v1/auth/refresh` y `POST /api/v1/ponds/{id}/temp-access`.
   Si la ruta no existe, la única respuesta aceptada es `404 internal_error`.
5. `test_expired_temp_token_rejected_by_mcp` y
   `test_revoked_temp_token_rejected_by_mcp`. Token vencido o revocado recibe
   MCP `401 agent_bad_credentials`.

## No tocar

`packages/contracts/**`, firmas de `commands/*`, migraciones Alembic,
`GET /plans` (catálogo público), flujos de confirmación SQL de #205 salvo lo
ya cableado.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

Issue #203 · statechart `docs/architecture/statecharts/pond-temp-access/` ·
pruebas en `apps/api/tests/test_temp_link_scope.py`.
