#!/usr/bin/env bash
# Host-side deploy. Refuses to run without a real env file and a real domain.
# Does not invent VPS, IP, or DNS. Call from the machine after it exists.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${KOI_PROD_ENV:-$ROOT/infra/env/prod.env}"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT/infra/docker-compose.prod.yml")

need() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" || "$value" == change-me* || "$value" == koicloud.example ]]; then
    echo "refusing deploy: $name is unset or still a placeholder" >&2
    echo "see docs/runbooks/deploy.md" >&2
    exit 1
  fi
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "refusing deploy: missing $ENV_FILE (copy infra/env/prod.env.example on the host)" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

need KOICLOUD_DOMAIN
need NODE_PUBLIC_HOST
need JWT_SECRET
need NODE_TOKEN
need POSTGRES_PASSWORD

cd "$ROOT"
git fetch --ff-only origin main
git merge --ff-only origin/main

mkdir -p /srv/koicloud/web /var/lib/koicloud/invoices /var/lib/koicloud/backups

if [[ -f "$ROOT/apps/web/package.json" ]]; then
  (cd "$ROOT/apps/web" && corepack enable && pnpm install --frozen-lockfile && pnpm build)
  rsync -a --delete "$ROOT/apps/web/dist/" /srv/koicloud/web/
fi

"${COMPOSE[@]}" up -d --build db api worker caddy
"${COMPOSE[@]}" exec -T api uv run alembic upgrade head

if [[ -f /etc/systemd/system/koicloud-agent.service ]] || systemctl list-unit-files | grep -q '^koicloud-agent.service'; then
  if git diff --name-only HEAD@{1} HEAD | grep -q '^apps/node-agent/'; then
    sudo systemctl restart koicloud-agent
  fi
fi

echo "compose is up on this host. Probe: curl -fsS https://${KOICLOUD_DOMAIN}/health"
echo "node-agent stays on systemd (see docs/runbooks/restart-agent.md)."
