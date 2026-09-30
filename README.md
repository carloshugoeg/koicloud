# KoiCloud

Monorepo de implementación de KoiCloud. Control plane (API + cola PG + node-agent),
web, CLI y contratos OpenAPI viven aquí.

## Estructura

- `apps/api` — FastAPI, migraciones Alembic y export OpenAPI
- `apps/web` — SPA React + Vite
- `apps/cli` — CLI `koicloud`
- `apps/node-agent` — node-agent con `mock_driver` y `docker_driver`
- `packages/contracts/openapi.json` — contrato exportado del backend
- `docs/architecture` — pack de arquitectura sellado
- `docs/tickets` — tickets por workstream

## Primeros comandos

```bash
make sync-rules
make up          # compose: db healthy → api migra → /api/v1/health
make migrate     # alembic upgrade head (host)
make seed        # migrate + usuario demo verificado
make contracts
make check
```

Credenciales demo tras `make seed`: `demo@koicloud.dev` / `Sup3rSegura!2026`.

## Pond local (sin VPS)

```bash
make pond-demo
psql "postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo"
```

E2E producto (Compose + DockerDriver):

```bash
bash scripts/demo-vivo.sh b
# o a mano: docs/runbooks/local-pond.md §2
```

## Autoría

Los commits se firman con la cuenta real de GitHub de quien hizo el trabajo.
`Equipo KoiCloud` es voz pública de docs y UI, no identidad de git.
