---
id: W1-53
workstream: W1
persona: Carlos Hugo Escobar
estado: en-revision
rama: w1-solid-review
epica: E10-01
sprint: S5
pr: https://github.com/carloshugoeg/koicloud/pull/238
depends_on:
---

# [W1-53] Revisión SOLID actualizada (módulos principales + refactors mínimos)

## Qué se ve

`docs/architecture/solid-review.md` cubre auth, billing/payments, ponds, metering, MCP/agent access y admin. Cada principio SOLID tiene un ejemplo cumplido y, si aplica, una violación, ambos con `ruta:línea` del árbol actual. Dos refactors sin cambio de comportamiento: comparación en tiempo constante del token de nodo, y partición del gate MCP. Pruebas nuevas del compare; suite MCP en verde.

## Entradas ya decididas (no se cambian)

- Módulos a revisar: auth, billing/payments, ponds/provisioning, metering, MCP/agent access, admin.
- Rama `w1-solid-review`.
- Sin cambios de OpenAPI, firmas de `commands/*`, migraciones, env ni deploys.
- Evitar archivos de PRs abiertos #235 (cuenta) y #236 (temp-link / `ponds/service.py`), y de `commands/auth.py` + plantillas de correo.
- Si un arreglo cambiaría comportamiento observable: documentarlo como recomendación, no implementarlo.

## Criterios de aceptación

1. `docs/architecture/solid-review.md` tiene sección por módulo con S·O·L·I·D y citas `path:line` verificadas.
2. Cada refactor aplicado aparece como antes → después con `file:line`.
3. `node_token_matches` usa `hmac.compare_digest`; hay pruebas en `tests/test_node_token_compare.py`.
4. El gate MCP separa autenticación pond-token vs agent-access; las pruebas MCP existentes pasan.
5. Ticket en `docs/tickets/w1/` con `estado: en-revision`; `make check-api` verde; PR draft contra `main`; sin merge en este ticket.

## No tocar

- `packages/contracts/openapi.json`, migraciones Alembic, `.env*`, `docker-compose.yml`, workflows de deploy.
- `apps/api/app/commands/auth.py`, plantillas de correo, `apps/web/src/features/account/**`.
- `apps/api/app/modules/ponds/service.py` y `apps/api/app/mcp/tools/list_tables.py` (conflicto con #236).
- Contratos congelados (rutas OpenAPI, firmas de commands, tablas/enums).

## Si algo falta

```
BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>
```

## Referencia

- Revisión previa: [W1-24](W1-24-solid-review.md) / PR #101.
- Plantilla de PR: `.github/PULL_REQUEST_TEMPLATE.md`.
