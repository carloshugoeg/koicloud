# Pond local (sin VPS)

El hito pide un pond alcanzable con `psql`. No hay credenciales de VPS en el
entorno. Hay dos caminos locales, ambos con Docker en la laptop:

| Camino | Qué hace | Cuándo usarlo |
|---|---|---|
| `make pond-demo` | Un `postgres:16-alpine` fijo en **15432** | Demo corta / fallback |
| `POST /ponds` + `AGENT_MODE=docker` | Control plane persistido + `DockerDriver` | Camino de producto (W1) |
| `AGENT_MODE=mock` | Cola + handlers en memoria | CI y laptops sin Docker |

Auth de login está persistido. Hace falta un usuario **verificado**.
`create_pond` upserta el usuario del JWT y adjunta el plan Micro si no hay
suscripción activa.

## 1. Pond de demostración (Compose, sin API)

```bash
make pond-demo
psql "postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo"
```

Servicio: `pond-demo` en `docker-compose.yml` (profile `ponds`). Contraseña de
desarrollo, no de producción.

## 2. E2E persistido: migrate → seed → login → `POST /ponds` → `psql`

Necesita Docker. El overlay monta el socket. Compose espera `db` healthy, corre
`alembic upgrade head` en `api`, y marca `api` healthy en `GET /api/v1/health`
antes de arrancar `node-agent`.

Atajo:

```bash
bash scripts/demo-vivo.sh b
```

A mano:

```bash
# 1. Control plane + node-agent con DockerDriver
AGENT_MODE=docker docker compose \
  -f docker-compose.yml \
  -f docker-compose.docker-agent.yml \
  up --build -d db api node-agent

# 2. Esperar readiness (contrato; también existe alias GET /health)
until curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null; do sleep 2; done

# 3. Usuario demo verificado (idempotente; corre migrate antes)
make seed
# demo@koicloud.dev / Sup3rSegura!2026

# 4. Login (solo el seed verificado; no “cualquier password”)
TOKEN=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@koicloud.dev","password":"Sup3rSegura!2026"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 5. Crear pond (primer puerto libre del rango 15000-15999)
curl -sS -X POST http://127.0.0.1:8000/api/v1/ponds \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"inventario-demo"}'

# 6. Esperar observed_state=running, luego:
curl -sS http://127.0.0.1:8000/api/v1/ponds/<pond_id>/connection \
  -H "Authorization: Bearer $TOKEN"
```

Credenciales del seed (también en `apps/api/tests/db_reset.py`):

| Campo | Valor |
|---|---|
| email | `demo@koicloud.dev` |
| password | `Sup3rSegura!2026` |
| estado | `active`, `email_verified_at` set |

Si registrás otro correo, el login exige verify (`email_not_verified`). Sin
mailer, leé el token `verify_email` en logs del API tras `POST /auth/register`,
luego `POST /auth/verify` con ese token.

La URI usa `postgres` / `NODE_PUBLIC_HOST` (default `127.0.0.1`) / el
`host_port` asignado / base `inventario_demo`. Ejemplo si tocó 15000:

```bash
psql "postgresql://postgres:<password>@127.0.0.1:15000/inventario_demo"
```

El contenedor se llama `koicloud-<nombre>`. El agent reclama el job en
`POST /internal/v1/jobs/claim` (`204` si no hay cola).

Health:

- Contrato y Compose healthcheck: `GET /api/v1/health`
- Alias ops (mismo cuerpo): `GET /health`

## 3. Driver docker (mock → real)

`apps/node-agent/agent/drivers/docker_driver.py` implementa el mismo ABC que
`mock_driver`. CI **no** lo corre contra un daemon: las pruebas inyectan un
cliente falso. `AGENT_MODE=mock` sigue siendo el default de CI.

## 4. Lo que sigue (no bloquea el hito local)

- Reset password sin mailer (token solo en logs / consola).
- Billing / SQL console / backups HTTP siguen siendo fixtures de contrato.
- Un VPS con `AGENT_MODE=docker` y `POND_PORT_RANGE_*` publicado, cuando existan
  host y credenciales reales. No inventar infra.
