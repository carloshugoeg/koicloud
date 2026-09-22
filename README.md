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

## Autoría

Los commits se firman con la cuenta real de GitHub de quien hizo el trabajo. `Equipo KoiCloud` es voz pública de docs y UI, no identidad de git.
