---
id: W1-13
workstream: W1
persona: Carlos
estado: hecho
rama: w1-infra-deploy
epica: "E10-02, E10-03"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/162"
depends_on:
---

# [W1-13] Infra: Caddy, compose de producción, systemd, `deploy.yml`

## Qué se ve

El repo queda listo para **una** VM Oracle Cloud Always Free (Ampere ARM, Ubuntu)
sin dominio de pago: hostname `<ip>.sslip.io` / `<ip>.nip.io`, Caddy con TLS,
ponds reales (`AGENT_MODE=docker`), reutilizando `.github/workflows/deploy.yml` y
ADR 003. **No** se ejecuta deploy real (la VM aún no existe). Runbook Despliegue
en `docs/runbooks/deploy.md` (Manual técnico §3; ENTREGA-2 §6.3).

## Entradas ya decididas (no se cambian)

- Esqueleto en `infra/` (Caddyfile, compose.prod, unit, env).
- `deploy.yml` gated on env; sin inventar IP/DNS en el workflow.
- Health post-deploy: `GET /health` o `GET /api/v1/health`.
- Host objetivo: Oracle Always Free + sslip.io (ADR 014). Render/Neon rechazados
  (sin Docker socket → sin ponds reales). Costo $0.
- Bases multi-arch (`postgres:16-alpine`, `python:3.12-slim`, `caddy:2.8-alpine`).

## Criterios de aceptación

1. `docker compose -f infra/docker-compose.prod.yml config` valida en local
   (`bash infra/scripts/check-prod-compose.sh` / `make check-infra`).
2. Caddyfile toma el hostname de `KOICLOUD_DOMAIN` (sslip.io/nip.io documentados);
   sin secretos en el repo.
3. Unit systemd del agent documentada; `AGENT_MODE=docker` para ponds reales.
4. Runbook Despliegue cubre: creación VM, puertos 80/443 y 15000-15999 (VCN +
   iptables), Docker, tabla de vars con cómo generar cada valor, GitHub
   `KOICLOUD_DEPLOY_HOST` / `_USER` / `_SSH_KNOWN_HOSTS` / `KOICLOUD_DEPLOY_SSH_KEY`,
   primer deploy, update, rollback. Sin IP inventada.
5. `ENVIRONMENT=production` rechaza defaults de `JWT_SECRET`, `POND_PASSWORD_KEY`,
   `NODE_TOKEN`, `MCP_DEMO_PASSWORD` al arrancar (`tests/test_production_secret_defaults.py`).
6. ADR 014 registra Oracle Always Free vs Render/Neon.
7. `npm run pregate` verde. Cableado SSH real queda pendiente hasta existir la VM
   (no fingir deploy).

## No tocar

Demo script (`scripts/demo-vivo.sh`) salvo punteros. Pack de presentación.
Credenciales / secretos de prod. Estado de otros tickets.

## Si algo falta

`BLOQUEADO: requiere host real (VPS) porque no hay máquina provisionada` — solo
si el criterio exige *ejecutar* el deploy. Preparar artefactos + runbook **no**
está bloqueado.

## Referencia

`docs/architecture/system-architecture.md` despliegue · `infra/` · E10-02/E10-03 ·
ENTREGA-2 §6.3 · ADR 003 · ADR 014.
