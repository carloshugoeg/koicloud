#!/usr/bin/env bash
# Client-side deploy. Idempotent. SSH host is required.
# Usage: bash infra/deploy.sh [-p port] [-i identity] [-l remote_path] user@host
# On the host: set infra/env/prod.env from infra/.env.production.example, then run this.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT=22
IDENTITY=""
REMOTE_PATH="${KOI_REMOTE_PATH:-/srv/koicloud}"
SSH_OPTS=(-o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)

usage() {
  echo "usage: $0 [-p port] [-i identity_file] [-l remote_path] user@host" >&2
  exit 2
}

while getopts ":p:i:l:h" opt; do
  case "$opt" in
    p) PORT="$OPTARG" ;;
    i) IDENTITY="$OPTARG" ;;
    l) REMOTE_PATH="$OPTARG" ;;
    h) usage ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))

HOST="${1:-}"
if [[ -z "$HOST" ]]; then
  usage
fi

if [[ -n "$IDENTITY" ]]; then
  SSH_OPTS+=(-i "$IDENTITY")
fi
SSH_OPTS+=(-p "$PORT")

SKIP_GIT="${KOI_DEPLOY_SKIP_GIT:-0}"
SKIP_WEB="${KOI_DEPLOY_SKIP_WEB:-0}"
CHECK_ONLY="${KOI_DEPLOY_CHECK_ONLY:-0}"
HTTP_PROXY="${KOI_DEPLOY_HTTP_PROXY:-0}"
PROD_ENV="${KOI_PROD_ENV:-$REMOTE_PATH/infra/env/prod.env}"

echo "deploy → ${HOST}:${PORT} path=${REMOTE_PATH}"
# shellcheck disable=SC2029
ssh "${SSH_OPTS[@]}" "$HOST" \
  "set -euo pipefail; cd $(printf %q "$REMOTE_PATH"); \
   KOI_DEPLOY_SKIP_GIT=$(printf %q "$SKIP_GIT") \
   KOI_DEPLOY_SKIP_WEB=$(printf %q "$SKIP_WEB") \
   KOI_DEPLOY_CHECK_ONLY=$(printf %q "$CHECK_ONLY") \
   KOI_DEPLOY_HTTP_PROXY=$(printf %q "$HTTP_PROXY") \
   KOI_PROD_ENV=$(printf %q "$PROD_ENV") \
   bash infra/scripts/deploy.sh"
