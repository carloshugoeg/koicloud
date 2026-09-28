---
id: W3-07
workstream: W3
persona: Jousé
estado: abierto
rama: w3-contratacion
epica: "E2-02, E2-05"
sprint: S3
pr:
depends_on: W3-01
---

# [W3-07] `POST /subscriptions` y `/cancel` (cableado)

## Qué se ve

Endpoints de contratación y cancelación al fin del período. Lo visible es el contrato HTTP correcto; el router transporta y el comando de W1 calcula.

## Entradas ya decididas (no se cambian)

- Depends on W3-01 (usuario real). Call `subscribe` and `cancel_subscription` only,
  even if the command body is still a fixture.
- Endpoints: `POST /subscriptions` -> `subscribe` y `POST /subscriptions/{id}/cancel` -> `cancel_subscription`.
- La contratación responde `{subscription, invoice, payment}`.
- CLI/MCP usan confirmación; Web no la requiere en esta ruta.
- Errores: `plan_required`, `quota_exceeded`, `confirmation_required` (solo para CLI/MCP).
- No se recalcula IVA ni prorrateo en el router.

## Criterios de aceptación

1. Subscribe devuelve la terna `{subscription, invoice, payment}` sin alterar payloads.
2. Cancel marca `cancel_at_period_end=true` y devuelve la suscripción actualizada.
3. Hay prueba de API para Micro happy path y ownership.
4. No aparece lógica de facturación nueva fuera del comando de W1.

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
