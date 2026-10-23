# Rollback manual de una migración Alembic

El deploy corre `alembic upgrade head` dentro del contenedor `api`
(`infra/scripts/deploy.sh`). **No** revierte solo. Si una migración deja
la API en 5xx / `/api/v1/ready` en 503, el equipo baja **un** revision a
mano y decide el siguiente paso.

Solo W1 escribe migraciones. Este runbook opera las que ya están en
`apps/api/alembic/versions/`. No reescribe `deploy.yml` ni inventa un
auto-rollback.

## 1. Confirmar el síntoma

```bash
curl -fsS "https://${KOICLOUD_DOMAIN}/api/v1/health" || true
curl -fsS "https://${KOICLOUD_DOMAIN}/api/v1/ready" || true

cd /srv/koicloud
docker compose --env-file infra/env/prod.env \
  -f infra/docker-compose.prod.yml \
  exec -T api uv run alembic current
docker compose --env-file infra/env/prod.env \
  -f infra/docker-compose.prod.yml \
  exec -T api uv run alembic history -v | head -40
```

Anotá la revision actual y la `down_revision` inmediata.

## 2. Respaldo de la base interna (antes de bajar)

```bash
bash infra/scripts/backup-internal-db.sh
ls -lt /var/lib/koicloud/backups/internal/ | head
```

Sin ese dump no sigas.

## 3. Downgrade de un paso

Sustituí `<down_revision>` por el id padre de la cabeza que falló
(por ejemplo, si la cabeza es `0004_billing_payment_port`, el padre es
`0003_billing_invoice_money`).

```bash
docker compose --env-file infra/env/prod.env \
  -f infra/docker-compose.prod.yml \
  exec -T api uv run alembic downgrade <down_revision>

docker compose --env-file infra/env/prod.env \
  -f infra/docker-compose.prod.yml \
  exec -T api uv run alembic current
```

Límites conocidos:

- Postgres **no** quita valores de un `ENUM` con seguridad. Un
  `downgrade` puede dejar el valor en el tipo (ver docstring de
  `0004_billing_payment_port`).
- Migraciones fusionadas **no** se reescriben: el arreglo es una
  migración nueva en un PR de W1, no un amend del archivo viejo.

## 4. Volver a servir y verificar

```bash
docker compose --env-file infra/env/prod.env \
  -f infra/docker-compose.prod.yml \
  up -d api worker

curl -fsS "https://${KOICLOUD_DOMAIN}/api/v1/health"
curl -fsS "https://${KOICLOUD_DOMAIN}/api/v1/ready"
```

Si el health sigue rojo, restaurá el dump interno (host + `pg_restore`
contra el servicio `db`) y escalá a W1. No encadenes varios
`downgrade` sin revisar el historial.

Puntero de deploy (sin inventar host): [`deploy.md`](./deploy.md).
