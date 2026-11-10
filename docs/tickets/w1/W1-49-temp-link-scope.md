---
id: W1-49
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-temp-link-scope
epica: "E9-02"
sprint: S8
pr:

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

1. Streamable HTTP `list_tables` con Basic temporal responde `agent_disabled`
   (no llega a trabajo contra el pond DB).
2. JSON-RPC niega `list_tables`, `list_ponds`, `get_usage` y `list_subscriptions`
   con `403 agent_disabled`.
3. `get_pond` del pond emitido funciona; el de otro pond del mismo dueño
   responde `pond_not_found`.
4. Basic temporal, en un cliente sin cookies de login, es rechazado en
   `/api/v1/me`, `/ponds`, detalle del pond, `/subscriptions`, `/admin/users`,
   `/auth/refresh` y `POST .../temp-access`.
5. Token vencido o revocado → MCP `401 agent_bad_credentials`.

## No tocar

`packages/contracts/**`, firmas de `commands/*`, migraciones Alembic,
`GET /plans` (catálogo público), flujos de confirmación SQL de #205 salvo lo
ya cableado.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

Issue #203 · statechart `docs/architecture/statecharts/pond-temp-access/` ·
pruebas en `apps/api/tests/test_temp_link_scope.py`.
