---
id: W3-08
workstream: W3
persona: Jousé
estado: en_revision
rama: w3-historiales
epica: "E2-06"
sprint: S3
pr: https://github.com/carloshugoeg/koicloud/pull/55
---

# [W3-08] `GET /subscriptions` y `GET /invoices`

## Qué se ve

Historial paginado de suscripciones e invoices del usuario autenticado. Lo visible es el envelope paginado, owner-only y con `example` consistente.

## Entradas ya decididas (no se cambian)

- Endpoints: `GET /subscriptions` y `GET /invoices`.
- Paginación canónica: `?cursor=&limit=50` y `next_cursor`.
- Solo devuelve filas del usuario autenticado.
- Los listados deben dejar ejemplos en OpenAPI.

## Criterios de aceptación

1. ~~Ambos endpoints aceptan `cursor` y `limit` y devuelven `next_cursor` cuando aplica.~~ **Descoped:** frozen OpenAPI has no `cursor`/`limit` query params on these GETs; lists currently return `next_cursor: null`. Needs a future CCR before AC#1 can land. Not inventing params in this ticket.
2. Nunca exponen rows de otro usuario.
3. Las pruebas cubren estado vacío y estado poblado.
4. Los schemas de lista quedan con `example` coherente.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
