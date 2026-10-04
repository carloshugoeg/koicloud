---
id: W1-13
workstream: W1
persona: Carlos
estado: abierto
rama: w1-infra-deploy
epica: "E10-02, E10-03"
sprint: S4
pr:
depends_on:
---

# [W1-13] Infra: Caddy, compose de producción, systemd, `deploy.yml`

## ESPERA — host real

`ESPERA: requires real host (VPS) — none provisioned by the team. Do not invent IP/DNS/provider.`
Stubs in `infra/` stay until a real host exists. No fake deploy.

## Qué se ve

`infra/docker-compose.prod.yml` deja de ser stub vacío. Caddy termina TLS y enruta
`/api`, `/mcp` y estáticos. Unit systemd del node-agent. Workflow `deploy.yml` documentado
para un **host real** ya provisionado por el equipo.

## Entradas ya decididas (no se cambian)

- Esqueleto en `infra/` (Caddyfile, compose.prod, unit, env).
- `deploy.yml` es de W4 con aprobación W1 (CODEOWNERS); este ticket prepara artefacto y
  runbook, no inventa máquina.
- Health post-deploy: `GET /health` o `GET /api/v1/health`.

## Criterios de aceptación

1. `docker compose -f infra/docker-compose.prod.yml config` valida en local.
2. Caddyfile enruta API + MCP según architecture; sin secretos en el repo.
3. Unit systemd del agent documentada en `docs/runbooks/`.
4. Runbook de deploy nombra el host **solo si ya existe**; si no hay VPS, el ticket sigue
   abierto y el PR solo deja compose/Caddy listos para cablear.

## Requires real host — do not invent VPS

No crear IP, DNS, ni provider ficticio. Sin host del curso/equipo: implementar archivos
locales + runbook y dejar `estado: abierto` hasta el cableado real. Nunca fingir deploy.

## No tocar

Demo script (`scripts/demo-vivo.sh`) salvo punteros. Pack de presentación. Credenciales.

## Si algo falta

`BLOQUEADO: requiere host real (VPS) porque no hay máquina provisionada` — y pará.

## Referencia

`docs/architecture/system-architecture.md` despliegue · `infra/` · E10-02/E10-03.
