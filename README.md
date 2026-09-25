# KoiCloud

Monorepo de implementación de KoiCloud. Esta Fase 0 congela contratos, scaffolds y tickets antes del trabajo paralelo por workstream.

## Estructura

- `apps/api` — FastAPI, contrato HTTP, migraciones y export OpenAPI
- `apps/web` — SPA React + Vite con la piel sellada
- `apps/cli` — CLI `koicloud`
- `apps/node-agent` — node-agent con `mock_driver` y `docker_driver`
- `packages/contracts/openapi.json` — contrato exportado del backend
- `docs/architecture` — pack de arquitectura sellado
- `docs/tickets` — tickets delegables por workstream

## Primeros comandos

```bash
make sync-rules
make contracts
make check-api
make check-web
make check-cli
make check-node-agent
```

## Pond local (hito vie 25, sin VPS)

CI y `docker compose up` siguen en `AGENT_MODE=mock`. Para un PostgreSQL 16 real
al que se pueda entrar con `psql` en la laptop:

```bash
make pond-demo
psql "postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo"
```

El node-agent ya tiene `DockerDriver` (mismo contrato que `mock_driver`). En una
máquina con socket Docker: overlay `docker-compose.docker-agent.yml`. Detalle:
[`docs/runbooks/local-pond.md`](docs/runbooks/local-pond.md). El E2E
register → Micro → `POST /ponds` persistido sigue pendiente de VPS + W3.

## Autoría

Los commits se firman con la cuenta real de GitHub de quien hizo el trabajo. `Equipo KoiCloud` es voz pública de docs y UI, no identidad de git.
