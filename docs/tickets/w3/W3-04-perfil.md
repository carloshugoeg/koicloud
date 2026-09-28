---
id: W3-04
workstream: W3
persona: Jousé
estado: abierto
rama: w3-perfil
epica: "E1-05"
sprint: S3
pr:
depends_on: W1-15
---

# [W3-04] `GET /me` y `PATCH /me`

## Qué se ve

Lectura y actualización del perfil del usuario autenticado. El resultado visible es que Web puede mostrar nombre, NIT, plan y cantidad de ponds desde un contrato estable.

## Entradas ya decididas (no se cambian)

- Depends on W1-15 landed. Call `get_me` and `update_profile` only.
- Endpoints: `GET /me` -> `get_me` y `PATCH /me` -> `update_profile`.
- Campos editables: `full_name` y `nit`.
- Response de `GET /me`: `{user, subscription?, ponds_count}`.
- Las `example` de request/response deben quedar en OpenAPI.
- NIT (congelado aquí): opcional. `strip()`. Vacío → `null`. Sin regex ni normalización
  de guiones. El comando guarda el string. El router no valida formato.

## Criterios de aceptación

1. El router llama `get_me`. Devuelve perfil, resumen de suscripción y cantidad de ponds.
2. El router llama `update_profile`. El comando persiste `full_name` y `nit`.
3. NIT vacío se guarda `null`. Cualquier otro string no vacío se transporta tal cual.
4. Hay `example` coherentes para request y response.
5. Las pruebas cubren get y patch feliz.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO` solo si hay que *editar* OpenAPI o la firma de un comando.
La regla de NIT está en *Entradas*. No abras CCR por un regex.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
