#!/usr/bin/env bash
# Prove infra/deploy.sh against a LOCAL SSH container (not a real VPS).
# Writes a run log under the path given as $1 (default ./deploy-local.log).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG="${1:-$ROOT/infra/scripts/deploy-local.log}"
NAME="koicloud-c0-deploy-target"
PORT="${KOI_PROOF_SSH_PORT:-2222}"
KEY_DIR="$(mktemp -d)"
IMAGE="koicloud-c0-sshd:local"

cleanup() {
  rm -rf "$KEY_DIR"
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -f "$ROOT/infra/env/prod.env"
}
trap cleanup EXIT

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

for _ in $(seq 1 40); do
  if ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -i "$KEY_DIR/id" -p "$PORT" root@127.0.0.1 'echo ssh-ok' 2>/dev/null; then
    break
  fi
  sleep 1
done

mkdir -p "$ROOT/infra/env"
cat >"$ROOT/infra/env/prod.env" <<EOF
POSTGRES_USER=koi
POSTGRES_PASSWORD=c0-local-proof-password-not-for-prod
POSTGRES_DB=koicloud
DATABASE_URL=postgresql+asyncpg://koi:c0-local-proof-password-not-for-prod@db:5432/koicloud
JWT_SECRET=c0-local-proof-jwt-secret-32bytes-min
REFRESH_TTL_DAYS=30
POND_PASSWORD_KEY=7chvGNh8l4rbVgpH0wWJjCT2J8eQ6D8eW5DiKjR3owE=
AGENT_MODE=docker
NODE_ID=node-c0-proof
NODE_TOKEN=c0-local-proof-node-token
KOICLOUD_DOMAIN=c0.local.test
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

{
  echo "=== Wave C0 local deploy proof $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "target: root@127.0.0.1:${PORT} (docker container $NAME)"
  echo "mode: KOI_DEPLOY_CHECK_ONLY=1 KOI_DEPLOY_SKIP_GIT=1 KOI_DEPLOY_SKIP_WEB=1 KOI_DEPLOY_HTTP_PROXY=1"
  KOI_DEPLOY_CHECK_ONLY=1 \
  KOI_DEPLOY_SKIP_GIT=1 \
  KOI_DEPLOY_SKIP_WEB=1 \
  KOI_DEPLOY_HTTP_PROXY=1 \
  bash "$ROOT/infra/deploy.sh" -p "$PORT" -i "$KEY_DIR/id" -l /srv/koicloud root@127.0.0.1
  echo "=== proof OK ==="
} 2>&1 | tee "$LOG"

echo "wrote $LOG"
