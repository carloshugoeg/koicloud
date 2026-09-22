---
id: W3-04
workstream: W3
persona: Jousé
estado: abierto
rama: w3-perfil
epica: "E1-05"
sprint: S3
pr:
---

# [W3-04] `GET /me` y `PATCH /me`

## Qué se ve

Lectura y actualización del perfil del usuario autenticado. El resultado visible es que Web puede mostrar nombre, NIT, plan y cantidad de ponds desde un contrato estable.

## Entradas ya decididas (no se cambian)

- Endpoints: `GET /me` -> `get_me` y `PATCH /me` -> `update_profile`.
- Campos editables: `full_name` y `nit`.
- Response de `GET /me`: `{user, subscription?, ponds_count}`.
- Las `example` de request/response deben quedar en OpenAPI.
- La validación exacta de NIT no está fijada en `api-surface.md`.

## Criterios de aceptación

1. `GET /me` devuelve perfil, resumen de suscripción y cantidad de ponds.
2. `PATCH /me` persiste `full_name` y `nit`.
3. La validación de NIT usa solo la regla congelada por W1, sin regex ad hoc.
4. Hay `example` coherentes para request y response.
5. Las pruebas cubren get y patch feliz.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.
- Si W1 no congela la regla de NIT, bloqueá el ticket y no inventes regex ni normalización nueva.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
