#!/usr/bin/env bash
# Prove infra/deploy.sh against a LOCAL SSH container (not a real VPS).
# Writes a run log under the path given as $1 (default ./deploy-local.log).
# Never touches infra/env/prod.env — uses a temp env via KOI_PROD_ENV.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG="${1:-$ROOT/infra/scripts/deploy-local.log}"
NAME="koicloud-c0-deploy-target"
PORT="${KOI_PROOF_SSH_PORT:-2222}"
KEY_DIR="$(mktemp -d)"
IMAGE="koicloud-c0-sshd:local"
PROOF_ENV_HOST="$ROOT/infra/env/prod.env.c0-proof"
PROOF_ENV_REMOTE="/srv/koicloud/infra/env/prod.env.c0-proof"
REAL_ENV="$ROOT/infra/env/prod.env"

cleanup() {
  rm -rf "$KEY_DIR"
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -f "$PROOF_ENV_HOST"
}
trap cleanup EXIT

if [[ -e "$REAL_ENV" ]]; then
  echo "refusing proof: $REAL_ENV already exists — will not overwrite a real prod.env" >&2
  echo "move it aside or unset KOI_PROOF_ALLOW; proof uses KOI_PROD_ENV → prod.env.c0-proof" >&2
  exit 1
fi

ssh-keygen -t ed25519 -N "" -f "$KEY_DIR/id" -q

cat >"$KEY_DIR/Dockerfile" <<'EOF'
FROM debian:bookworm-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      openssh-server bash ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd /root/.ssh \
    && printf '%s\n' 'PermitRootLogin yes' 'PasswordAuthentication no' 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config \
    && ssh-keygen -A
COPY id.pub /root/.ssh/authorized_keys
RUN chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys
EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
EOF

docker build -t "$IMAGE" -f "$KEY_DIR/Dockerfile" "$KEY_DIR"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" \
  -p "127.0.0.1:${PORT}:22" \
  -v "$ROOT:/srv/koicloud:rw" \
  "$IMAGE" >/dev/null

ssh-keygen -R "[127.0.0.1]:${PORT}" >/dev/null 2>&1 || true

for _ in $(seq 1 40); do
  if ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -i "$KEY_DIR/id" -p "$PORT" root@127.0.0.1 'echo ssh-ok' 2>/dev/null; then
    break
  fi
  sleep 1
done

mkdir -p "$ROOT/infra/env"
cat >"$PROOF_ENV_HOST" <<EOF
POSTGRES_USER=koi
POSTGRES_PASSWORD=c0-local-proof-password-not-for-prod
POSTGRES_DB=koicloud
DATABASE_URL=postgresql+asyncpg://koi:c0-local-proof-password-not-for-prod@db:5432/koicloud
JWT_SECRET=c0-local-proof-jwt-secret-32bytes-min
REFRESH_TTL_DAYS=30
POND_PASSWORD_KEY=c0-local-proof-fernet-key-not-default==
AGENT_MODE=docker
NODE_ID=node-c0-proof
NODE_TOKEN=c0-local-proof-node-token
KOICLOUD_DOMAIN=localhost
NODE_PUBLIC_HOST=127.0.0.1
POND_PORT_RANGE_START=15000
POND_PORT_RANGE_END=15999
MCP_ENABLED=true
MCP_DEMO_PASSWORD=c0-local-proof-mcp-demo
EMAIL_PROVIDER=resend
PAYMENT_PROVIDER=simulated
INVOICE_DIR=/var/lib/koicloud/invoices
BACKUP_DIR=/var/lib/koicloud/backups
INTERNAL_API_URL=http://127.0.0.1:8000/internal/v1
EOF

{
  echo "=== Wave C0 local deploy proof $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "target: root@127.0.0.1:${PORT} (docker container $NAME)"
  echo "env: KOI_PROD_ENV=${PROOF_ENV_REMOTE} (never infra/env/prod.env)"
  echo "mode: KOI_DEPLOY_CHECK_ONLY=1 KOI_DEPLOY_SKIP_GIT=1 KOI_DEPLOY_SKIP_WEB=1 KOI_DEPLOY_HTTP_PROXY=1"
  KOI_PROD_ENV="$PROOF_ENV_REMOTE" \
  KOI_DEPLOY_CHECK_ONLY=1 \
  KOI_DEPLOY_SKIP_GIT=1 \
  KOI_DEPLOY_SKIP_WEB=1 \
  KOI_DEPLOY_HTTP_PROXY=1 \
  bash "$ROOT/infra/deploy.sh" -p "$PORT" -i "$KEY_DIR/id" -l /srv/koicloud root@127.0.0.1
  echo "=== proof OK ==="
} 2>&1 | tee "$LOG"

echo "wrote $LOG"
