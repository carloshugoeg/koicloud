---
id: W1-16
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-teammate-unblock-semana
epica: "S2 unblock"
sprint: S2
pr:
depends_on:
---

# [W1-16] Desbloqueo teammates: MSW, tickets honestos, `list_plans`

## Qué se ve

Jason puede pintar W2-04/W2-08 contra MSW con ≥6 `observed_state` y ≥3 backups.
El índice W1 y W1-09 dejan de mentir sobre andamio. `GET /plans` lee la tabla `plans`
seed. Onboarding apunta a los quirks Mac/VM ya fijados en `scripts/demo-vivo.sh`.

## Entradas ya decididas (no se cambian)

- OpenAPI / firmas de comandos no cambian.
- Demo A/B path (`make pond-demo`, `scripts/demo-vivo.sh`) no se reescribe.
- Subscribe, backups HTTP, SQL, metering siguen fixtures.
- Sin VPS inventado.

## Criterios de aceptación

1. `apps/web/src/mocks/fixtures.ts` tiene ≥6 ponds con `observed_state` distintos y ≥3 backups (`daily`, `on_demand`, `pre_delete`).
2. `docs/tickets/w1/W1-09-pond-lifecycle.md` ya no dice que delete/retry son andamio.
3. `GET /api/v1/plans` devuelve filas seed (`sandbox`, `micro`, `pro`).
4. `docs/agent-onboarding.md` + `docs/runbooks/demo-vivo.md` documentan quirks operativos.
5. `make check-api` y `make check-web` verdes.

## No tocar

Pack de presentación del Project store. Rutas W2/W3/W4 de producto salvo docs/tickets
que W1 corrige por honesty. `packages/contracts/**` a mano.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

`docs/runbooks/local-pond.md`, `scripts/demo-vivo.sh`, audit store `docs/poteto-semana-analisis.md`.
