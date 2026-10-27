#!/usr/bin/env bash
# Boot the Wave C0 e2e compose stack, run the suite, collect artifacts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e/lib.sh
source "$SCRIPT_DIR/lib.sh"

export E2E_REPORT_DIR="${E2E_REPORT_DIR:-$REPORT_DIR}"
mkdir -p "$E2E_REPORT_DIR"

cleanup() {
  if [[ "${E2E_KEEP_STACK:-0}" != "1" ]]; then
    log "tearing down compose stack"
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

log "building + starting e2e compose stack"
KOI_DB_HOST_PORT="${KOI_DB_HOST_PORT:-55432}" \
  "${COMPOSE[@]}" up -d --build db api worker node-agent \
  | tee "$E2E_REPORT_DIR/compose-up.log"

log "waiting for api health"
if ! wait_http "${API_BASE}/health" 180; then
  "${COMPOSE[@]}" ps -a >"$E2E_REPORT_DIR/compose-ps.txt" || true
  "${COMPOSE[@]}" logs --tail 200 >"$E2E_REPORT_DIR/compose-logs.txt" || true
  die "api never became healthy"
fi
ok "api healthy"

bash "$SCRIPT_DIR/suite.sh" | tee "$E2E_REPORT_DIR/suite.log"
ok "e2e run complete"
