#!/usr/bin/env bash
# AC2: host apply (infra/scripts/deploy.sh) is safe to re-run.
# Runs check-only twice against a temp env with non-placeholder values.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

IDEM_ENV="$(mktemp)"
trap 'rm -f "$IDEM_ENV"' EXIT

cat >"$IDEM_ENV" <<'EOF'
POSTGRES_USER=koi
POSTGRES_PASSWORD=c0-idempotent-check-password-not-prod
POSTGRES_DB=koicloud
DATABASE_URL=postgresql+asyncpg://koi:c0-idempotent-check-password-not-prod@db:5432/koicloud
JWT_SECRET=c0-idempotent-check-jwt-secret-32b
REFRESH_TTL_DAYS=30
POND_PASSWORD_KEY=c0-idempotent-check-fernet-key-not-default==
AGENT_MODE=docker
NODE_ID=node-c0-idem
NODE_TOKEN=c0-idempotent-check-node-token
KOICLOUD_DOMAIN=localhost
NODE_PUBLIC_HOST=127.0.0.1
POND_PORT_RANGE_START=15000
POND_PORT_RANGE_END=15999
MCP_ENABLED=true
MCP_DEMO_PASSWORD=c0-idempotent-check-mcp-demo
EMAIL_PROVIDER=resend
PAYMENT_PROVIDER=simulated
INVOICE_DIR=/var/lib/koicloud/invoices
BACKUP_DIR=/var/lib/koicloud/backups
INTERNAL_API_URL=http://127.0.0.1:8000/internal/v1
EOF

run_once() {
  local n="$1"
  echo "=== deploy check-only pass $n ==="
  KOI_PROD_ENV="$IDEM_ENV" \
  KOI_DEPLOY_CHECK_ONLY=1 \
  KOI_DEPLOY_SKIP_GIT=1 \
  KOI_DEPLOY_SKIP_WEB=1 \
  KOI_DEPLOY_HTTP_PROXY=1 \
    bash "$ROOT/infra/scripts/deploy.sh"
}

run_once 1
run_once 2
echo "deploy.sh host apply re-runnable (check-only ×2) OK"
