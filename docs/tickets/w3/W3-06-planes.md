---
id: W3-06
workstream: W3
persona: Jousé
estado: hecho
rama: w3-planes
epica: "E2-01"
sprint: S2
pr:
---

# [W3-06] `GET /plans` y valores de la semilla

## Qué se ve

Endpoint público para catálogo de planes. El resultado visible es que Web/CLI reciben Sandbox, Micro y Pro desde la semilla sellada, sin lógica adicional en el router.

## Entradas ya decididas (no se cambian)

- Endpoint: `GET /plans` -> `list_plans`.
- La fuente es la migración `0002_seed_plans`.
- Planes y límites fijos: Sandbox, Micro y Pro según propuesta §1.5 y mockup `#planes`.
- La respuesta es pública y no requiere auth.

## Criterios de aceptación

1. Devuelve una lista ordenada de tres planes.
2. Los valores coinciden exactamente con la semilla.
3. OpenAPI deja `example` en el schema `Plan`.
4. Hay prueba de API comparando contra el fixture/semilla.

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
