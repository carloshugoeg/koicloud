---
id: W1-56
workstream: W1
persona: Carlos
estado: hecho
rama: w1-temp-link-list-ponds
epica: E9-02
sprint: S8
pr: https://github.com/carloshugoeg/koicloud/pull/249
depends_on:
---

# [W1-56] Temp link: whoami + list_ponds del pond fijado

## Qué se ve

Un agente (Claude Code) conectado con un link temporal pond-scoped recibe el
pond fijado en `whoami` y puede llamar `list_ponds`, que devuelve solo ese pond.
Ya no recibe `agent_disabled` al listar ponds. Acceso a otro pond sigue
`pond_not_found`. `create_pond`, `/me` y revoke no cambian. Tokens normales
(no temp-link) no cambian.

## Entradas ya decididas (no se cambian)

- `TEMP_ACCESS_SCOPES` gana `list_ponds` (sigue en `apps/api/app/schemas.py`).
- `AuthContext.pond_id` ya pinnea el actor; `list_for_user` ya filtra por él.
- Tokens viejos sin `list_ponds` en la fila lo reciben al autenticar (como
  `confirm_action` con `run_sql`).
- Sin migración. Sin CCR de OpenAPI ni cambio de firmas de `commands/*`.

## Criterios de aceptación

1. `test_temp_whoami_includes_pinned_pond`: MCP `whoami` con Basic temporal
   incluye `pond.id` y `pond.name` del pond emitido.
2. `test_temp_list_ponds_returns_only_pinned_pond`: MCP `list_ponds` responde
   200 con exactamente un pond (el fijado), no `agent_disabled`.
3. `test_temp_get_pond_other_still_pond_not_found`: `get_pond` de otro pond del
   mismo dueño responde `pond_not_found`.
4. `test_temp_create_pond_still_agent_disabled`: `create_pond` sigue
   `403 agent_disabled`.
5. `npm run pregate` verde. Tokens JWT / agent_access normales sin cambio
   observable.

## No tocar

`packages/contracts/**`, firmas de `commands/*`, migraciones Alembic,
rama `w1-onboarding-tour` (#245), rebase / force-push.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

Bug en demo en vivo (Nov 11): Claude Code + temp link → `whoami` ok,
`list_ponds` → `agent_disabled`. Pruebas en
`apps/api/tests/test_temp_link_list_ponds.py`. Antecedente W1-50 / #236.
