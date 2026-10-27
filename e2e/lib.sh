#!/usr/bin/env bash
# Shared helpers for the compose e2e suite.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_BASE="${API_BASE:-http://127.0.0.1:8000/api/v1}"
COMPOSE_FILES=(
  -f "$ROOT/docker-compose.yml"
  -f "$ROOT/docker-compose.docker-agent.yml"
  -f "$ROOT/e2e/docker-compose.override.yml"
)
COMPOSE=(docker compose "${COMPOSE_FILES[@]}")
REPORT_DIR="${E2E_REPORT_DIR:-$ROOT/e2e/artifacts}"
mkdir -p "$REPORT_DIR"

log() { printf '[e2e] %s\n' "$*"; }
die() { printf '[e2e] FAIL: %s\n' "$*" >&2; exit 1; }
ok() { printf '[e2e] OK: %s\n' "$*"; }

py_json() {
  python3 -c "import json,sys; ${1}"
}

api_post() {
  local path="$1"
  local body="$2"
  local token="${3:-}"
  local surface="${4:-}"
  local extra=()
  [[ -n "$token" ]] && extra+=(-H "Authorization: Bearer $token")
  [[ -n "$surface" ]] && extra+=(-H "X-KOI-Surface: $surface")
  curl -sS -X POST "${API_BASE}${path}" \
    -H 'Content-Type: application/json' \
    "${extra[@]}" \
    -d "$body"
}

api_get() {
  local path="$1"
  local token="${2:-}"
  local extra=()
  [[ -n "$token" ]] && extra+=(-H "Authorization: Bearer $token")
  curl -sS "${API_BASE}${path}" "${extra[@]}"
}

api_delete() {
  local path="$1"
  local token="$2"
  local surface="${3:-cli}"
  curl -sS -X DELETE "${API_BASE}${path}" \
    -H "Authorization: Bearer $token" \
    -H "X-KOI-Surface: $surface"
}

wait_http() {
  local url="$1"
  local tries="${2:-90}"
  local i=0
  while (( i < tries )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    i=$((i + 2))
  done
  return 1
}

extract_verify_token() {
  local email="$1"
  local try=0
  local token=""
  while (( try < 30 )); do
    token="$(
      "${COMPOSE[@]}" logs api 2>&1 \
        | grep "verify_email token for ${email}:" \
        | tail -1 \
        | sed -E 's/.*verify_email token for [^:]*: //' \
        || true
    )"
    [[ -n "$token" ]] && break
    sleep 1
    try=$((try + 1))
  done
  [[ -n "$token" ]] || die "no verify_email token in api logs for $email"
  echo "$token"
}

poll_pond_running() {
  local pond_id="$1"
  local token="$2"
  local state="" i=0
  while (( i < 180 )); do
    state="$(
      api_get "/ponds/$pond_id" "$token" \
        | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('observed_state') or '')" \
        2>/dev/null || true
    )"
    log "pond state=$state"
    [[ "$state" == "running" ]] && return 0
    sleep 3
    i=$((i + 3))
  done
  return 1
}

poll_backup_succeeded() {
  local pond_id="$1"
  local backup_id="$2"
  local token="$3"
  local status="" i=0
  while (( i < 180 )); do
    status="$(
      api_get "/ponds/$pond_id/backups" "$token" \
        | py_json "
d=json.load(sys.stdin)
want='$backup_id'
for b in d.get('backups') or []:
  if b.get('id')==want:
    print(b.get('status') or '')
    break
" 2>/dev/null || true
    )"
    log "backup status=$status"
    [[ "$status" == "succeeded" ]] && return 0
    [[ "$status" == "failed" ]] && return 1
    sleep 3
    i=$((i + 3))
  done
  return 1
}
