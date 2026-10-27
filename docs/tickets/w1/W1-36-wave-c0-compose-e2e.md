---
id: W1-36
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-wave-c0-compose-e2e
epica: "E10-02, E10-03"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/140"
depends_on:
---

# [W1-36] Wave C0: compose prod, deploy.sh SSH, e2e compose CI

## Qué se ve

Un solo PR deja listo el camino VPS sin inventar host: compose de producción +
Caddy, `infra/deploy.sh user@host` idempotente, `.env.production.example` solo
con nombres de secretos, healthchecks, y un job CI `e2e-compose` que corre el
flujo registro → plan → Simular pago → pond running → SQL → backup → delete
contra un stack compose local. En un VPS real: copiar env y correr `deploy.sh`.

## Entradas ya decididas (no se cambian)

- Rama existente: `w1-wave-c0-compose-e2e` (nombre histórico del wave; slug del ticket).
- Alcance: `infra/` + `e2e/` (+ workflow `e2e-compose` mínimo). Sin tocar apps A1/A2.
- `PAYMENT_PROVIDER` obligatorio en prod: compose sin default `:-simulated`; `deploy.sh` lo exige con `need`.
- No inventar IP/DNS; proof de deploy solo contra contenedor SSH local.
- No mergear este PR desde el agente; ship tras LGTM + gate (+ ventana Carlos, lane alta).

## Criterios de aceptación

1. `bash infra/scripts/check-prod-compose.sh` OK (compose + Caddy + names-only env).
2. `infra/deploy.sh` toma `user@host`; host apply en `infra/scripts/deploy.sh` es idempotente.
3. `infra/.env.production.example` lista cada secreto sin valores.
4. Healthchecks en db/api/worker/caddy; worker no usa `pgrep python` genérico.
5. Job CI `e2e-compose` verde: registro → plan → pago simulado → pond → SQL → backup → delete.
6. `proof-local-deploy.sh` usa `KOI_PROD_ENV` temporal; rechaza si existe `infra/env/prod.env`.

## No tocar

`apps/**` de olas A1/A2. Contratos OpenAPI / firmas de commands. Host VPS real.
Tickets de otros workstreams (p. ej. W2-14).

## Si algo falta

`BLOQUEADO: requiere CCR porque …` solo si hay que editar contrato congelado.
Sin host real: el ticket no inventa VPS; el Done de CI es el compose e2e local.

## Referencia

W1-13 groundwork · `docs/runbooks/deploy.md` · PR #140 · polish Phase 4 Wave C0.
(Renombrado desde W1-27: ese id ya lo ocupa Plan pricing / PR #123.)
