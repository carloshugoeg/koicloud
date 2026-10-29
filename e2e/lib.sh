#!/usr/bin/env bash
# Shared helpers for the compose e2e suite.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_BASE="${API_BASE:-http://127.0.0.1:8000/api/v1}"
COMPOSE=(docker compose -f "$ROOT/e2e/docker-compose.yml")
REPORT_DIR="${E2E_REPORT_DIR:-$ROOT/e2e/artifacts}"
mkdir -p "$REPORT_DIR"

log() { printf '[e2e] %s\n' "$*"; }
die() { printf '[e2e] FAIL: %s\n' "$*" >&2; exit 1; }
ok() { printf '[e2e] OK: %s\n' "$*"; }

py_json() {
  python3 -c "import json,sys; ${1}"
}

# Last HTTP status survives command-substitution subshells via this file.
API_HTTP_FILE="${REPORT_DIR}/.last-http"

last_http() {
  cat "$API_HTTP_FILE" 2>/dev/null || echo ""
}

# HTTP helpers always capture status. Non-2xx dies unless allow_http lists the code.
# Broken confirm / 4xx / 5xx therefore cannot print OK downstream.
_api_curl() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local token="${4:-}"
  local surface="${5:-}"
  local allow_http="${6:-}"
  local tmp code args=()
  tmp="$(mktemp)"
  args=(-sS -o "$tmp" -w "%{http_code}" -X "$method" "${API_BASE}${path}")
  [[ -n "$token" ]] && args+=(-H "Authorization: Bearer $token")
  [[ -n "$surface" ]] && args+=(-H "X-KOI-Surface: $surface")
  if [[ -n "$body" ]]; then
    args+=(-H 'Content-Type: application/json' -d "$body")
  fi
  code="$(curl "${args[@]}")" || {
    rm -f "$tmp"
    printf '%s\n' "000" >"$API_HTTP_FILE"
    die "curl transport failed $method $path"
  }
  printf '%s\n' "$code" >"$API_HTTP_FILE"
  if [[ "$code" =~ ^2 ]]; then
    cat "$tmp"
    rm -f "$tmp"
    return 0
  fi
  if [[ -n "$allow_http" ]]; then
    local allowed=0 a
    for a in $allow_http; do
      if [[ "$code" == "$a" ]]; then
        allowed=1
        break
      fi
    done
    if (( allowed )); then
      cat "$tmp"
      rm -f "$tmp"
      return 0
    fi
  fi
  printf '[e2e] FAIL: HTTP %s %s %s body=%s\n' "$code" "$method" "$path" "$(head -c 500 "$tmp")" >&2
  rm -f "$tmp"
  exit 1
}

api_post() {
  local path="$1"
  local body="$2"
  local token="${3:-}"
  local surface="${4:-}"
  local allow_http="${5:-}"
  _api_curl POST "$path" "$body" "$token" "$surface" "$allow_http"
}

api_get() {
  local path="$1"
  local token="${2:-}"
  local allow_http="${3:-}"
  _api_curl GET "$path" "" "$token" "" "$allow_http"
}

api_delete() {
  local path="$1"
  local token="$2"
  local surface="${3:-cli}"
  local allow_http="${4:-}"
  _api_curl DELETE "$path" "" "$token" "$surface" "$allow_http"
}

wait_http() {
  # Readiness probe only (-f fails on HTTP errors). Suite calls use _api_curl
  # status checks; do not use --fail-with-body here (host curl quirks on CI).
  local url="$1"
  local tries="${2:-90}"
  local i=0
  local last=""
  while (( i < tries )); do
    if last="$(curl -fsS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)"; then
      [[ "$last" =~ ^2 ]] && return 0
    fi
    sleep 2
    i=$((i + 2))
  done
  log "wait_http gave up on $url (last_http=${last:-none})"
  return 1
}

extract_verify_token() {
  local email="$1"
  local try=0
  local token=""
  while (( try < 45 )); do
    token="$(
      "${COMPOSE[@]}" logs api --no-color 2>&1 \
        | grep -F "verify_email token for ${email}:" \
        | tail -1 \
        | sed -E 's/.*verify_email token for [^:]*:[[:space:]]*//' \
        | tr -d '\r' \
        | awk '{print $1}' \
        || true
    )"
    token="${token%%[[:space:]]*}"
    [[ -n "$token" ]] && break
    sleep 1
    try=$((try + 1))
  done
  if [[ -z "$token" ]]; then
    "${COMPOSE[@]}" logs api --no-color --tail 80 >"$REPORT_DIR/api-logs-no-verify.txt" || true
    die "no verify_email token in api logs for $email"
  fi
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

# After delete confirm: wait until GET is 404 or observed_state/desired_state is deleted.
poll_pond_gone() {
  local pond_id="$1"
  local token="$2"
  local i=0 body state desired code
  while (( i < 180 )); do
    body="$(api_get "/ponds/$pond_id" "$token" "404")"
    code="$(last_http)"
    if [[ "$code" == "404" ]]; then
      log "pond GET → 404"
      return 0
    fi
    state="$(
      echo "$body" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('observed_state') or '')" 2>/dev/null || true
    )"
    desired="$(
      echo "$body" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('desired_state') or '')" 2>/dev/null || true
    )"
    log "pond after-delete observed=$state desired=$desired http=$code"
    if [[ "$state" == "deleted" || "$desired" == "deleted" ]]; then
      return 0
    fi
    sleep 3
    i=$((i + 3))
  done
  return 1
}
