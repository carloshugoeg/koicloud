#!/usr/bin/env bash
# Validates infra/docker-compose.prod.yml without contacting a host.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE="${DOCKER_COMPOSE:-}"
if [[ -z "$COMPOSE" ]]; then
  if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
  else
    echo "docker compose is required for this check" >&2
    exit 1
  fi
fi

# Names-only example must not be fed to compose (empty overrides defaults).
CHECK_ENV="$(mktemp)"
trap 'rm -f "$CHECK_ENV"' EXIT
cat >"$CHECK_ENV" <<'EOF'
POSTGRES_USER=koi
POSTGRES_PASSWORD=change-me
POSTGRES_DB=koicloud
DATABASE_URL=postgresql+asyncpg://koi:change-me@db:5432/koicloud
JWT_SECRET=change-me-32-random-bytes
REFRESH_TTL_DAYS=30
POND_PASSWORD_KEY=change-me-fernet-key
AGENT_MODE=docker
NODE_ID=node-prod
NODE_TOKEN=change-me
KOICLOUD_DOMAIN=koicloud.example
NODE_PUBLIC_HOST=change-me-public-host
POND_PORT_RANGE_START=15000
POND_PORT_RANGE_END=15999
MCP_ENABLED=true
EMAIL_PROVIDER=console
PAYMENT_PROVIDER=simulated
INVOICE_DIR=/var/lib/koicloud/invoices
BACKUP_DIR=/var/lib/koicloud/backups
INTERNAL_API_URL=http://127.0.0.1:8000/internal/v1
EOF

$COMPOSE --env-file "$CHECK_ENV" \
  -f "$ROOT/infra/docker-compose.prod.yml" config >/tmp/koicloud-prod-compose.yml

$COMPOSE --env-file "$CHECK_ENV" \
  -f "$ROOT/infra/docker-compose.prod.yml" \
  -f "$ROOT/infra/docker-compose.http.yml" config >/tmp/koicloud-http-compose.yml

python3 - <<'PY'
from pathlib import Path

text = Path("/tmp/koicloud-prod-compose.yml").read_text(encoding="utf-8")
http = Path("/tmp/koicloud-http-compose.yml").read_text(encoding="utf-8")
caddy = Path("infra/Caddyfile").read_text(encoding="utf-8")
caddy_http = Path("infra/Caddyfile.http").read_text(encoding="utf-8")
env_names = Path("infra/.env.production.example").read_text(encoding="utf-8")
missing = []
for token in ("db:", "api:", "worker:", "caddy:"):
    if token not in text:
        missing.append(f"compose missing {token}")
if "127.0.0.1:8000" not in text:
    missing.append("api must bind loopback :8000 only")
if "healthcheck" not in text:
    missing.append("compose missing healthcheck blocks")
for token in ("handle /api/", "handle /mcp", "respond @internal 403", "handle /health"):
    if token not in caddy:
        missing.append(f"Caddyfile missing {token}")
if "koicloud.example" not in caddy:
    missing.append("Caddyfile must keep architecture domain placeholder")
if ":80" not in caddy_http:
    missing.append("Caddyfile.http must bind :80")
if 'published: "8080"' not in http and "published: 8080" not in http and "8080:80" not in http:
    missing.append("http overlay must publish host port 8080")
for name in (
    "POSTGRES_PASSWORD",
    "JWT_SECRET",
    "NODE_TOKEN",
    "POND_PASSWORD_KEY",
    "KOICLOUD_DOMAIN",
    "NODE_PUBLIC_HOST",
):
    if f"{name}=" not in env_names:
        missing.append(f".env.production.example missing {name}")
    # No values: line must be NAME= with nothing after (optional spaces).
for line in env_names.splitlines():
    if not line or line.lstrip().startswith("#"):
        continue
    if "=" not in line:
        missing.append(f"env line without =: {line}")
        continue
    key, _, val = line.partition("=")
    if val.strip():
        missing.append(f".env.production.example must have no values ({key})")
if missing:
    raise SystemExit("\n".join(missing))
print("prod compose + Caddyfile + http overlay + names-only env OK")
PY
