#!/usr/bin/env bash
# Daily dump of the control-plane Postgres. Runs on the host cron, not GitHub.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${KOI_PROD_ENV:-$ROOT/infra/env/prod.env}"
DEST="${BACKUP_DIR:-/var/lib/koicloud/backups}/internal"
STAMP="$(date -u +%Y%m%d)"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

mkdir -p "$DEST"
docker compose --env-file "$ENV_FILE" -f "$ROOT/infra/docker-compose.prod.yml" exec -T db \
  pg_dump -U "${POSTGRES_USER:-koi}" -d "${POSTGRES_DB:-koicloud}" -Fc \
  >"$DEST/${STAMP}.dump"

find "$DEST" -name '*.dump' -mtime +7 -delete
echo "wrote $DEST/${STAMP}.dump"
