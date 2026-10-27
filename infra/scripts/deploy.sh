#!/usr/bin/env bash
# Host-side apply. Idempotent: safe to re-run. Refuses placeholders.
# Invoked by infra/deploy.sh over SSH, or directly on the machine.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${KOI_PROD_ENV:-$ROOT/infra/env/prod.env}"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT/infra/docker-compose.prod.yml")
if [[ "${KOI_DEPLOY_HTTP_PROXY:-0}" == "1" ]]; then
  COMPOSE+=(-f "$ROOT/infra/docker-compose.http.yml")
fi

need() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" || "$value" == change-me* || "$value" == koicloud.example ]]; then
    echo "refusing deploy: $name is unset or still a placeholder" >&2
    echo "see docs/runbooks/deploy.md and infra/.env.production.example" >&2
    exit 1
  fi
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "refusing deploy: missing $ENV_FILE (copy infra/.env.production.example → infra/env/prod.env)" >&2
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
need POND_PASSWORD_KEY
need PAYMENT_PROVIDER

cd "$ROOT"

if [[ "${KOI_DEPLOY_SKIP_GIT:-0}" != "1" ]]; then
  git fetch --ff-only origin main
  git merge --ff-only origin/main
fi

WEB_ROOT="${KOI_WEB_ROOT:-/srv/koicloud/web}"
DATA_ROOT="${KOI_DATA_ROOT:-/var/lib/koicloud}"

if [[ "${KOI_DEPLOY_CHECK_ONLY:-0}" == "1" ]]; then
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    "${COMPOSE[@]}" config >/dev/null
    echo "deploy check-only OK on $(hostname) (env + compose config valid)"
  else
    echo "deploy check-only OK on $(hostname) (env valid; docker compose not in PATH — skip config)"
  fi
  exit 0
fi

mkdir -p "$WEB_ROOT" "$DATA_ROOT/invoices" "$DATA_ROOT/backups"

if [[ "${KOI_DEPLOY_SKIP_WEB:-0}" != "1" && -f "$ROOT/apps/web/package.json" ]]; then
  (cd "$ROOT/apps/web" && corepack enable && pnpm install --frozen-lockfile && pnpm build)
  rsync -a --delete "$ROOT/apps/web/dist/" "$WEB_ROOT/"
elif [[ "${KOI_DEPLOY_SKIP_WEB:-0}" == "1" ]]; then
  mkdir -p "$WEB_ROOT"
  if [[ ! -f "$WEB_ROOT/index.html" ]]; then
    printf '%s\n' '<!doctype html><title>KoiCloud</title><p>web stub</p>' >"$WEB_ROOT/index.html"
  fi
fi

"${COMPOSE[@]}" up -d --build db api worker caddy
"${COMPOSE[@]}" exec -T api uv run alembic upgrade head

if [[ -f /etc/systemd/system/koicloud-agent.service ]] || systemctl list-unit-files 2>/dev/null | grep -q '^koicloud-agent.service'; then
  if [[ "${KOI_DEPLOY_SKIP_GIT:-0}" != "1" ]] && git diff --name-only HEAD@{1} HEAD 2>/dev/null | grep -q '^apps/node-agent/'; then
    sudo systemctl restart koicloud-agent
  fi
fi

echo "compose is up on this host. Probe: curl -fsS https://${KOICLOUD_DOMAIN}/health"
echo "node-agent stays on systemd (see docs/runbooks/restart-agent.md)."
