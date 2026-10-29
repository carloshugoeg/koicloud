#!/usr/bin/env bash
# Validates infra/docker-compose.prod.yml without contacting a host.
# Also proves EMAIL_PROVIDER=console is rejected before traffic under prod.
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
# Happy path uses a non-console provider — console must not reach prod apply.
# Override KOI_CHECK_EMAIL_PROVIDER=console only to prove the check refuses it.
CHECK_EMAIL_PROVIDER="${KOI_CHECK_EMAIL_PROVIDER:-resend}"
CHECK_ENV="$(mktemp)"
BAD_CONSOLE_ENV="$(mktemp)"
trap 'rm -f "$CHECK_ENV" "$BAD_CONSOLE_ENV"' EXIT
cat >"$CHECK_ENV" <<EOF
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
EMAIL_PROVIDER=${CHECK_EMAIL_PROVIDER}
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
prod_src = Path("infra/docker-compose.prod.yml").read_text(encoding="utf-8")
if "EMAIL_PROVIDER:-console" in prod_src or "EMAIL_PROVIDER: ${EMAIL_PROVIDER:-console}" in prod_src:
    missing.append("prod compose must not default EMAIL_PROVIDER to console")
if "PAYMENT_PROVIDER:-simulated" in prod_src:
    missing.append("prod compose must not default PAYMENT_PROVIDER to simulated")
# Gate r7: ENVIRONMENT must be pinned so Settings console guard actually fires.
if "ENVIRONMENT: production" not in prod_src:
    missing.append("prod compose must pin ENVIRONMENT: production on services")
# Rendered config must carry ENVIRONMENT=production into the api container.
env_ok = any("ENVIRONMENT" in line and "production" in line for line in text.splitlines())
if not env_ok:
    missing.append("rendered prod compose must set ENVIRONMENT=production for api")
# With ENVIRONMENT=production, EMAIL_PROVIDER=console must not pass this check.
if any(
    line.strip() in {"EMAIL_PROVIDER: console", "EMAIL_PROVIDER:console"}
    or line.strip().startswith("EMAIL_PROVIDER:") and "console" in line
    for line in text.splitlines()
):
    missing.append(
        "EMAIL_PROVIDER=console is not allowed when ENVIRONMENT=production "
        "(startup would refuse; use a real provider in prod.env)"
    )
deploy_src = Path("infra/scripts/deploy.sh").read_text(encoding="utf-8")
if "need EMAIL_PROVIDER" not in deploy_src:
    missing.append("deploy.sh must need EMAIL_PROVIDER")
if "need PAYMENT_PROVIDER" not in deploy_src:
    missing.append("deploy.sh must need PAYMENT_PROVIDER")
if '== "console"' not in deploy_src:
    missing.append("deploy.sh must refuse EMAIL_PROVIDER=console before compose up")
if missing:
    raise SystemExit("\n".join(missing))
print("prod compose + Caddyfile + http overlay + names-only env OK")
PY

# Negative: prod env with console must fail before serving traffic.
# Use non-placeholder host values so need() reaches the console guard.
cat >"$BAD_CONSOLE_ENV" <<'EOF'
POSTGRES_USER=koi
POSTGRES_PASSWORD=c0-console-reject-password-not-prod
POSTGRES_DB=koicloud
DATABASE_URL=postgresql+asyncpg://koi:c0-console-reject-password-not-prod@db:5432/koicloud
JWT_SECRET=c0-console-reject-jwt-secret-32bytes
REFRESH_TTL_DAYS=30
POND_PASSWORD_KEY=7chvGNh8l4rbVgpH0wWJjCT2J8eQ6D8eW5DiKjR3owE=
AGENT_MODE=docker
NODE_ID=node-c0-console-reject
NODE_TOKEN=c0-console-reject-node-token
KOICLOUD_DOMAIN=localhost
NODE_PUBLIC_HOST=127.0.0.1
POND_PORT_RANGE_START=15000
POND_PORT_RANGE_END=15999
MCP_ENABLED=true
EMAIL_PROVIDER=console
PAYMENT_PROVIDER=simulated
INVOICE_DIR=/var/lib/koicloud/invoices
BACKUP_DIR=/var/lib/koicloud/backups
INTERNAL_API_URL=http://127.0.0.1:8000/internal/v1
EOF
set +e
KOI_PROD_ENV="$BAD_CONSOLE_ENV" \
KOI_DEPLOY_CHECK_ONLY=1 \
KOI_DEPLOY_SKIP_GIT=1 \
KOI_DEPLOY_SKIP_WEB=1 \
KOI_DEPLOY_HTTP_PROXY=1 \
  bash "$ROOT/infra/scripts/deploy.sh" >/tmp/koicloud-console-deploy.out 2>/tmp/koicloud-console-deploy.err
console_rc=$?
set -e
if [[ "$console_rc" -eq 0 ]]; then
  echo "expected deploy.sh to refuse EMAIL_PROVIDER=console under prod; got exit 0" >&2
  cat /tmp/koicloud-console-deploy.out /tmp/koicloud-console-deploy.err >&2 || true
  exit 1
fi
if ! grep -q 'EMAIL_PROVIDER=console' /tmp/koicloud-console-deploy.err; then
  echo "deploy.sh refusal message missing EMAIL_PROVIDER=console" >&2
  cat /tmp/koicloud-console-deploy.err >&2 || true
  exit 1
fi
echo "deploy.sh correctly refuses EMAIL_PROVIDER=console before traffic (exit $console_rc)"
