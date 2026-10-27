#!/usr/bin/env bash
# Full happy-path e2e against a running local compose stack.
# Flow: registro → plan → Simular pago → pond running → SQL → backup → delete
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e/lib.sh
source "$SCRIPT_DIR/lib.sh"

EMAIL="${E2E_EMAIL:-e2e-$(date +%s)@koicloud.test}"
PASSWORD="${E2E_PASSWORD:-E2eSegura!2026}"
POND_NAME="${E2E_POND_NAME:-e2e-pond}"
TRACE="$REPORT_DIR/trace.jsonl"
: >"$TRACE"

trace() {
  local step="$1"
  local detail="$2"
  printf '{"ts":"%s","step":"%s","detail":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$step" \
    "$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$detail")" \
    | tee -a "$TRACE" >/dev/null
  log "$step — $detail"
}

trace "health" "GET /api/v1/health"
curl -fsS "${API_BASE}/health" | tee "$REPORT_DIR/health.json" >/dev/null \
  || die "api health failed"
ok "health"

trace "registro" "POST /auth/register $EMAIL"
REG_JSON="$(api_post "/auth/register" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"E2E Wave C0\"}")"
echo "$REG_JSON" | tee "$REPORT_DIR/register.json" >/dev/null
echo "$REG_JSON" | py_json "d=json.load(sys.stdin); assert d.get('email_verified') is False" \
  || die "register shape"
ok "registro"

trace "verify" "extract token + POST /auth/verify"
VERIFY_TOKEN="$(extract_verify_token "$EMAIL")"
VERIFY_JSON="$(api_post "/auth/verify" "{\"token\":\"$VERIFY_TOKEN\"}")"
echo "$VERIFY_JSON" | tee "$REPORT_DIR/verify.json" >/dev/null
echo "$VERIFY_JSON" | py_json "d=json.load(sys.stdin); assert d.get('email_verified') is True" \
  || die "verify failed"
ok "verify"

trace "login" "POST /auth/login"
TOKEN="$(
  api_post "/auth/login" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
    | tee "$REPORT_DIR/login.json" \
    | py_json "print(json.load(sys.stdin)['access_token'])"
)"
[[ -n "$TOKEN" ]] || die "no access_token"
ok "login"

trace "plan" "GET /plans"
PLANS_JSON="$(api_get "/plans")"
echo "$PLANS_JSON" | tee "$REPORT_DIR/plans.json" >/dev/null
echo "$PLANS_JSON" | py_json "
d=json.load(sys.stdin)
ids=[p.get('id') for p in (d.get('plans') or [])]
assert 'micro' in ids, ids
" || die "plans missing micro"
ok "plan"

trace "simular_pago" "POST /subscriptions plan_id=micro (payment.method=simulated)"
SUB_JSON="$(api_post "/subscriptions" '{"plan_id":"micro"}' "$TOKEN")"
echo "$SUB_JSON" | tee "$REPORT_DIR/subscribe.json" >/dev/null
echo "$SUB_JSON" | py_json "
d=json.load(sys.stdin)
sub=d.get('subscription') or {}
inv=d.get('invoice') or {}
pay=d.get('payment') or {}
assert sub.get('status')=='active', sub
assert inv.get('status')=='paid', inv
assert pay.get('method')=='simulated', pay
assert pay.get('status')=='succeeded', pay
" || die "Simular pago / subscribe failed"
ok "Simular pago"

trace "pond_create" "POST /ponds name=$POND_NAME"
POND_JSON="$(api_post "/ponds" "{\"name\":\"$POND_NAME\"}" "$TOKEN")"
echo "$POND_JSON" | tee "$REPORT_DIR/pond-create.json" >/dev/null
POND_ID="$(
  echo "$POND_JSON" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or '')"
)"
if [[ -z "$POND_ID" ]]; then
  POND_NAME="${POND_NAME}-$(date +%s)"
  POND_JSON="$(api_post "/ponds" "{\"name\":\"$POND_NAME\"}" "$TOKEN")"
  echo "$POND_JSON" | tee "$REPORT_DIR/pond-create.json" >/dev/null
  POND_ID="$(
    echo "$POND_JSON" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or '')"
  )"
fi
[[ -n "$POND_ID" ]] || die "no pond id"
ok "pond created $POND_ID"

trace "pond_running" "poll observed_state=running"
poll_pond_running "$POND_ID" "$TOKEN" || {
  "${COMPOSE[@]}" logs --tail 120 api worker node-agent >"$REPORT_DIR/pond-timeout-logs.txt" || true
  die "pond did not reach running"
}
api_get "/ponds/$POND_ID" "$TOKEN" | tee "$REPORT_DIR/pond-running.json" >/dev/null
ok "pond running"

trace "sql" "POST /ponds/{id}/sql SELECT 1"
SQL_JSON="$(api_post "/ponds/$POND_ID/sql" '{"query":"SELECT 1 AS n","mode":"read"}' "$TOKEN")"
echo "$SQL_JSON" | tee "$REPORT_DIR/sql.json" >/dev/null
echo "$SQL_JSON" | py_json "
d=json.load(sys.stdin)
assert d.get('row_count', 0) >= 1 or (d.get('rows') and len(d['rows'])>=1), d
" || die "sql failed"
ok "sql"

trace "backup" "POST /ponds/{id}/backups + poll succeeded"
BACKUP_JSON="$(api_post "/ponds/$POND_ID/backups" '{}' "$TOKEN")"
echo "$BACKUP_JSON" | tee "$REPORT_DIR/backup-create.json" >/dev/null
BACKUP_ID="$(
  echo "$BACKUP_JSON" | py_json "d=json.load(sys.stdin); b=d.get('backup') or {}; print(b.get('id') or '')"
)"
[[ -n "$BACKUP_ID" ]] || die "no backup id"
poll_backup_succeeded "$POND_ID" "$BACKUP_ID" "$TOKEN" || {
  "${COMPOSE[@]}" logs --tail 120 node-agent >"$REPORT_DIR/backup-timeout-logs.txt" || true
  die "backup did not succeed"
}
ok "backup $BACKUP_ID"

trace "delete" "DELETE pond propose→confirm→GET gone"
# Propose returns 409 confirmation_required (CLI surface). Any other 4xx/5xx dies.
DEL_JSON="$(api_delete "/ponds/$POND_ID" "$TOKEN" "cli" "409")"
echo "$DEL_JSON" | tee "$REPORT_DIR/delete-propose.json" >/dev/null
[[ "$(last_http)" == "409" ]] || die "delete propose expected HTTP 409, got $(last_http)"
echo "$DEL_JSON" | py_json "d=json.load(sys.stdin); assert d.get('status')=='confirmation_required', d" \
  || die "delete propose status"
CONFIRM_TOKEN="$(
  echo "$DEL_JSON" | py_json "d=json.load(sys.stdin); print(d.get('token') or '')"
)"
[[ -n "$CONFIRM_TOKEN" ]] || die "delete did not return confirmation token"
# Confirm must be 2xx. Broken confirm (4xx/5xx) exits before OK.
CONFIRM_JSON="$(api_post "/confirm/$CONFIRM_TOKEN" '{}' "$TOKEN")"
CONFIRM_HTTP="$(last_http)"
echo "$CONFIRM_JSON" | tee "$REPORT_DIR/delete-confirm.json" >/dev/null
echo "$CONFIRM_HTTP" >"$REPORT_DIR/delete-confirm.http"
[[ "$CONFIRM_HTTP" =~ ^2 ]] || die "delete confirm expected 2xx, got $CONFIRM_HTTP"
ok "delete confirmed HTTP $CONFIRM_HTTP"
poll_pond_gone "$POND_ID" "$TOKEN" || {
  "${COMPOSE[@]}" logs --tail 120 api worker node-agent >"$REPORT_DIR/delete-timeout-logs.txt" || true
  die "pond still present after delete confirm"
}
ok "delete verified GET 404/deleted"

cat >"$REPORT_DIR/summary.json" <<EOF
{
  "email": "$EMAIL",
  "pond_id": "$POND_ID",
  "backup_id": "$BACKUP_ID",
  "steps": ["registro","plan","simular_pago","pond_running","sql","backup","delete"],
  "result": "pass"
}
EOF

ok "suite passed — report $REPORT_DIR"
