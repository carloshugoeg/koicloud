---
id: W1-12
workstream: W1
persona: Carlos
estado: hecho
rama: w1-mcp-gate-confirm
epica: "E9-02, E9-03, E9-04"
sprint: S4
pr: "#27; follow-ups #38"
depends_on:
---

# [W1-12] MCP: montaje, gate, prompt, tools mutantes y confirmaciones

## Qué se ve

`/mcp` deja de ser skeleton. FastMCP (o montaje equivalente in-process) expone tools que
delegan en `commands/*`. El gate autentica slug+password. Toda tool mutante responde
`confirmation_required` con `token` + `summary`; `confirm_action(token)` consume
`pending_confirmations` y ejecuta el comando real. `GET /mcp` (info) lista tools leídas y
mutantes. El prompt de sistema vive en `prompt.py`.

## Entradas ya decididas (no se cambian)

- Diseño: `system-architecture.md` §4.3, `api-surface.md` §4 y §6, `AGENTS.md` §6.
- Tools mutantes de W1 (mínimo vertical): `create_pond`, `delete_pond`, `confirm_action`,
  `cancel_confirmation`. Lecturas de referencia W1 puede dejar (`whoami`, `list_ponds`,
  `get_pond`) para que `/mcp` sea útil; el resto de lecturas es W4-07.
- Cada tool ≤ 25 líneas; cero lógica de negocio en la tool.
- `pending_confirmations` ya migrada; ORM + `propose`/`confirm` persisten (no fixtures).
- Gate: Basic `slug:password` o `X-KOI-Agent-Password`; errores `agent_disabled` /
  `agent_bad_credentials`. Demo settings (`mcp_demo_slug` / `mcp_demo_password`) válidos
  hasta que `agent_access` persista (puede ser follow-up del mismo ticket o nota en PR).
- W4 no toca `server.py` / `gate.py` / `prompt.py` ni tools mutantes.

## Criterios de aceptación

1. Gate rechaza credenciales malas y acepta las demo (o fila `agent_access` habilitada).
2. Tool de lectura (`whoami` o `list_ponds`) devuelve shape de contrato sin mutar.
3. `create_pond` (MCP) → `confirmation_required` con token persistido; sin ejecutar create.
4. `confirm_action(token)` consume el pendiente y encola create real (`202` / pond+job).
5. Token expirado o desconocido → `confirmation_expired` / `confirmation_not_found`.
6. Pruebas in-process (FastAPI TestClient y/o FastMCP) cubren gate + propose + confirm.
7. `make check-api` verde.

## Slice aceptable si el PR no cierra todo

Info + lecturas mínimas + propose/confirm para `create_pond` (y cancel). Dejar en este
ticket (sección follow-up del PR) lo diferido: mount Streamable HTTP puro, rotate gate
persistido, `restore_backup` / `run_sql` write MCP, delete con summary rico.

### Follow-up (post vertical slice)

- [x] Montar FastMCP ASGI Streamable HTTP en `/mcp` sin romper OpenAPI `mcp_info`
  (hybrid ASGI: `Accept: text/event-stream` → FastMCP; GET/POST OpenAPI intactos).
- [x] Persistir `agent_access` (slug/password argon2 por usuario); gate lee la tabla
  (bootstrap demo slug/password solo si aún no hay fila).
- [x] Tools mutantes: `restore_backup`, `run_sql` (write → propose); summary de delete
  con estado observado + `pre_delete`.
- W4-07 añade el resto de lecturas copiando el patrón de `server.py`.

## No tocar

`apps/web/**`, `apps/cli/**`, tools de solo lectura reservadas a W4-07 salvo el mínimo de
referencia. Pack de presentación. OpenAPI editado a mano (usar `make contracts`).

## Si algo falta

Respondé `BLOQUEADO` solo si falta un comando HTTP que la tool deba llamar y no existe
firma. No inventes VPS ni OAuth.

## Referencia

`docs/architecture/system-architecture.md` §4.3 · `interconnections.md` §4 · skeleton actual
en `apps/api/app/mcp/`.
