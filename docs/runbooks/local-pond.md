# Pond local (sin VPS)

El hito del viernes pide un pond alcanzable con `psql`. No hay credenciales de VPS
en este entorno. El camino que sí avanza el producto, sin inventar infra:

| Camino | Qué hace | Cuándo usarlo |
|---|---|---|
| `AGENT_MODE=mock` | Cola + handlers en memoria | CI y laptops sin Docker |
| `make pond-demo` | Un `postgres:16-alpine` en el puerto **15432** | Demo local / `psql` hoy |
| `AGENT_MODE=docker` | `DockerDriver` crea ponds reales por job | Laptop o VPS con socket Docker |

## 1. Pond de demostración (Compose)

```bash
make pond-demo
psql "postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo"
```

Servicio: `pond-demo` en `docker-compose.yml` (profile `ponds`). Imagen congelada
`postgres:16-alpine`. Contraseña de desarrollo, no de producción.

## 2. Driver docker (mock → real)

`apps/node-agent/agent/drivers/docker_driver.py` implementa el mismo ABC que
`mock_driver`: `create_pond`, `start`, `stop`, `delete`, `dump`, `restore`, `sample`.
CI **no** lo corre contra un daemon: las pruebas inyectan un cliente falso.

En una máquina con Docker:

```bash
AGENT_MODE=docker docker compose \
  -f docker-compose.yml \
  -f docker-compose.docker-agent.yml \
  up
```

El overlay monta `/var/run/docker.sock`. Cada job `create_pond` levanta
`koicloud-<nombre>` y espera `pg_isready`.

## 3. Lo que todavía necesita Carlos / VPS

- Persistencia real de `create_pond` (hoy el comando de API sigue en el andamio
  `build_pond` / `build_job` de Fase 0).
- Register → suscripción Micro → `POST /ponds` contra control plane (W3-01 + W3-07).
- Un VPS con `AGENT_MODE=docker` y el rango `POND_PORT_RANGE_*` publicado.

Hasta entonces, `make pond-demo` es el `psql` del hito. No sustituye el E2E de
producción; evita bloquear el viernes por falta de VPS.
