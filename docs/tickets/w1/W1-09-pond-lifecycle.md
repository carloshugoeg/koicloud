---
id: W1-09
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-persist-create-pond
epica: E3-01
sprint: S1
pr:
---

# [W1-09] `create_pond` persistido + job claim

## Qué se ve

`POST /api/v1/ponds` deja de devolver fixtures. Inserta `ponds` + `pond_status` + `jobs(create_pond, queued)`. El node-agent reclama el job (`204` si la cola está vacía) y al completar el pond pasa a `observed_state=running`. `GET /ponds/{id}/connection` devuelve host/puerto/password reales para `psql`.

## Entradas ya decididas (no se cambian)

- Firma de `commands.create_pond` / `list_ponds` / `get_pond` / `get_connection`.
- OpenAPI: `202 {pond, job}`, errores `plan_required`, `quota_exceeded`, `pond_name_taken`, `node_unavailable`.
- `DELETE /ponds` y retry siguen en andamio Fase 0.
- Driver `postgres:16-alpine` ya en `main` (`DockerDriver`).
- Auth/register/subscribe de W3 siguen fixtures; este ticket upserta el usuario del JWT y adjunta Micro si no hay suscripción.

## Criterios de aceptación

1. `POST /ponds` (Web) responde `202` con pond `pending` y job `queued` persistidos.
2. Nombre repetido → `409 pond_name_taken`. Segundo pond en Micro → `409 quota_exceeded`.
3. `POST /internal/v1/jobs/claim` sin jobs → `204`. Con job → payload `create_pond`.
4. Complete succeeded → `observed_state=running` y `GET .../connection` usable.
5. `make check-api` y `make check-node-agent` verdes.

## No tocar

OpenAPI/schemas congelados, migraciones ya fusionadas, pantallas W2, billing W3 salvo el puente Micro.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

`docs/architecture/interconnections.md` §2 y `docs/runbooks/local-pond.md`.
