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

$COMPOSE --env-file "$ROOT/infra/env/prod.env.example" \
  -f "$ROOT/infra/docker-compose.prod.yml" config >/tmp/koicloud-prod-compose.yml

python3 - <<'PY'
from pathlib import Path

text = Path("/tmp/koicloud-prod-compose.yml").read_text(encoding="utf-8")
caddy = Path("infra/Caddyfile").read_text(encoding="utf-8")
missing = []
for token in ("db:", "api:", "worker:", "caddy:"):
    if token not in text:
        missing.append(f"compose missing {token}")
if "127.0.0.1:8000" not in text:
    missing.append("api must bind loopback :8000 only")
for token in ("handle /api/", "handle /mcp", "respond @internal 403", "handle /health"):
    if token not in caddy:
        missing.append(f"Caddyfile missing {token}")
if "koicloud.example" not in caddy:
    missing.append("Caddyfile must keep architecture domain placeholder")
if missing:
    raise SystemExit("\n".join(missing))
print("prod compose + Caddyfile template OK")
PY
