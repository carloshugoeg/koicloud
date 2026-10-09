#!/usr/bin/env bash
# KoiCloud — demo en vivo a prueba de fallos (Mac/Linux + Docker)
# Uso (desde el clone, o con KOICLOUD_ROOT):
#   bash path/to/demo-vivo.sh preflight
#   bash path/to/demo-vivo.sh reset
#   bash path/to/demo-vivo.sh a          # Demo A (siempre)
#   bash path/to/demo-vivo.sh b          # Demo B (control plane)
#   bash path/to/demo-vivo.sh all        # reset → A → B
#   bash path/to/demo-vivo.sh full       # register → Micro → pond (Entrega final)
#   bash path/to/demo-vivo.sh entrega    # reset → full (ensayo completo API)
#   bash path/to/demo-vivo.sh s3         # S3 happy path: subscribe → usage → PDF+IVA → backup → restore
#   bash path/to/demo-vivo.sh s3-entrega # reset → s3
#   bash path/to/demo-vivo.sh sql        # solo SQL inventario en pond-demo
#   bash path/to/demo-vivo.sh warm       # deja A caliente sin SQL
#
# Flags:
#   FORCE=1   mata el proceso que escucha el puerto (último recurso)
#   SKIP_GIT=1  no hace pull
#
# Creds Demo B / S3 (post-seed): demo@koicloud.dev / Sup3rSegura!2026

set -euo pipefail

DEMO_EMAIL="${DEMO_EMAIL:-demo@koicloud.dev}"
DEMO_PASSWORD="${DEMO_PASSWORD:-Sup3rSegura!2026}"
# Distinct from pond-demo container name `koicloud-inventario-demo` so A+B can coexist.
DEMO_POND_NAME="${DEMO_POND_NAME:-pond-api-demo}"
FULL_DEMO_EMAIL="${FULL_DEMO_EMAIL:-presenter-$(date +%Y%m%d-%H%M%S)@koicloud.dev}"
FULL_DEMO_PASSWORD="${FULL_DEMO_PASSWORD:-Sup3rSegura!2026}"
FULL_DEMO_NAME="${FULL_DEMO_NAME:-Presentador Demo}"
FULL_DEMO_POND="${FULL_DEMO_POND:-inventario-demo}"
POND_URI="${POND_URI:-postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo}"
DB_URL_HOST="${DATABASE_URL:-postgresql+asyncpg://koi:koi@127.0.0.1:5432/koicloud}"
API_BASE="${API_BASE:-http://127.0.0.1:8000/api/v1}"
COMPOSE_B=(docker compose -f docker-compose.yml -f docker-compose.docker-agent.yml)

use_hostnet_overlay_if_needed() {
  [[ "${FORCE_HOSTNET:-0}" == "1" ]] || {
    # After db is up, probe container→db. Failure ⇒ hostnet overlay (cloud VM quirk).
    # Match THIS project's network only — `_default$` falsely hits crm-core_default etc.
    local net
    net="$(docker network ls --format '{{.Name}}' | grep -E '^koicloud_default$' | head -1 || true)"
    [[ -n "$net" ]] || return 0
    if docker run --rm --network "$net" postgres:16-alpine \
        pg_isready -h db -U koi -d koicloud >/dev/null 2>&1; then
      return 0
    fi
  }
  # hostnet overlay hardcodes 127.0.0.1:5432 — incompatible with KOI_DB_HOST_PORT remap
  if [[ "${KOI_DB_HOST_PORT:-5432}" != "5432" ]]; then
    warn "bridge probe falló pero KOI_DB_HOST_PORT=${KOI_DB_HOST_PORT} — no uso hostnet (quedate en bridge)"
    return 0
  fi
  [[ -f docker-compose.vm-hostnet.yml ]] || return 0
  warn "Usando overlay docker-compose.vm-hostnet.yml (bridge TCP roto o FORCE_HOSTNET=1)"
  COMPOSE_B=(docker compose -f docker-compose.yml -f docker-compose.docker-agent.yml -f docker-compose.vm-hostnet.yml)
}

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; BLU=$'\033[34m'; RST=$'\033[0m'
ok()   { echo "${GRN}✓${RST} $*"; }
warn() { echo "${YLW}!${RST} $*"; }
err()  { echo "${RED}✗${RST} $*" >&2; }
info() { echo "${BLU}→${RST} $*"; }
die()  { err "$*"; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Falta comando: $1"
}

find_root() {
  if [[ -n "${KOICLOUD_ROOT:-}" && -f "${KOICLOUD_ROOT}/Makefile" ]]; then
    cd "$KOICLOUD_ROOT"
    return
  fi
  if [[ -f ./Makefile && -f ./docker-compose.yml ]]; then
    return
  fi
  if [[ -f "$HOME/koicloud/Makefile" ]]; then
    cd "$HOME/koicloud"
    return
  fi
  die "No encuentro el repo. cd ~/koicloud o export KOICLOUD_ROOT=..."
}

port_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true
  fi
}

# lsof often misses listeners owned by other users (e.g. EDB postgres on macOS).
port_accepts() {
  local port="$1"
  if command -v nc >/dev/null 2>&1 && nc -z 127.0.0.1 "$port" >/dev/null 2>&1; then
    return 0
  fi
  (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1
}

port_in_use() {
  local port="$1"
  local pids
  pids="$(port_pids "$port")"
  [[ -n "$pids" ]] && return 0
  port_accepts "$port"
}

docker_ids_on_port() {
  local port="$1"
  docker ps --format '{{.ID}} {{.Ports}}' 2>/dev/null \
    | awk -v p=":$port->" '$0 ~ p { print $1 }' \
    || true
  docker ps --format '{{.ID}} {{.Ports}}' 2>/dev/null \
    | awk -v p="0.0.0.0:$port->" '$0 ~ p { print $1 }' \
    || true
  docker ps --format '{{.ID}} {{.Ports}}' 2>/dev/null \
    | awk -v p="[::]:$port->" '$0 ~ p { print $1 }' \
    || true
}

free_port() {
  local port="$1"
  local label="${2:-port $port}"
  if ! port_in_use "$port"; then
    ok "$label libre ($port)"
    return 0
  fi
  warn "$label ocupado ($port) — liberando…"

  # 1) Contenedores Docker que publican el puerto
  local id
  for id in $(docker_ids_on_port "$port" | sort -u); do
    [[ -z "$id" ]] && continue
    info "docker stop $id"
    docker stop "$id" >/dev/null || true
  done

  # 2) Contenedores koicloud conocidos
  docker ps -aq --filter name=koicloud 2>/dev/null | while read -r cid; do
    [[ -z "$cid" ]] && continue
    if docker port "$cid" 2>/dev/null | grep -qE ":${port}\b"; then
      info "docker stop (koicloud) $cid"
      docker stop "$cid" >/dev/null || true
    fi
  done

  sleep 1
  if ! port_in_use "$port"; then
    ok "$label liberado"
    return 0
  fi

  # 3) FORCE=1 mata PID(s)
  if [[ "${FORCE:-0}" == "1" ]]; then
    local pid
    for pid in $(port_pids "$port"); do
      warn "FORCE=1 → kill $pid (puerto $port)"
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
  fi

  if port_in_use "$port"; then
    err "Puerto $port sigue ocupado:"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
    die "Cerrá Postgres.app / brew services stop postgresql@XX, o reintentá con FORCE=1 $0 …"
  fi
  ok "$label liberado"
}

wait_http() {
  local url="$1"
  local secs="${2:-90}"
  local i=0
  info "Esperando $url (hasta ${secs}s)…"
  while (( i < secs )); do
    if curl -sf "$url" >/dev/null 2>&1; then
      ok "HTTP OK: $url"
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  err "Timeout esperando $url"
  ${COMPOSE_B[@]} logs api --tail 60 || true
  return 1
}

wait_tcp() {
  local host="$1" port="$2" secs="${3:-60}"
  local i=0
  info "Esperando $host:${port}…"
  while (( i < secs )); do
    if (echo >/dev/tcp/"$host"/"$port") >/dev/null 2>&1; then
      ok "$host:$port acepta conexiones"
      return 0
    fi
    # bash /dev/tcp may fail on some shells — fallback nc/curl
    if command -v nc >/dev/null 2>&1 && nc -z "$host" "$port" 2>/dev/null; then
      ok "$host:$port acepta conexiones"
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

ensure_docker() {
  need_cmd docker
  if ! docker info >/dev/null 2>&1; then
    die "Docker no responde. Abrí Docker Desktop y esperá a Running."
  fi
  ok "Docker OK"
}

py_json() {
  python3 -c "import json,sys; $1" "$@"
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

extract_verify_token() {
  local email="$1"
  local try=0
  local token=""
  while (( try < 20 )); do
    token="$(
      "${COMPOSE_B[@]}" logs api 2>&1 \
        | grep "verify_email token for ${email}:" \
        | tail -1 \
        | sed -E 's/.*verify_email token for [^:]*: //' \
        || true
    )"
    [[ -n "$token" ]] && break
    sleep 1
    try=$((try + 1))
  done
  [[ -n "$token" ]] || die "no encontré verify_email token en logs del api para $email"
  echo "$token"
}

login_token() {
  local email="$1"
  local password="$2"
  api_post "/auth/login" "{\"email\":\"$email\",\"password\":\"$password\"}" \
    | py_json "print(json.load(sys.stdin)['access_token'])"
}

poll_pond_running() {
  local pond_id="$1"
  local token="$2"
  local state="" i=0
  while (( i < 90 )); do
    state="$(
      api_get "/ponds/$pond_id" "$token" \
        | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('observed_state') or d.get('status') or '')" \
        2>/dev/null || true
    )"
    echo "  state=$state"
    [[ "$state" == "running" ]] && return 0
    sleep 2
    i=$((i + 2))
  done
  return 1
}

poll_backup_status() {
  local pond_id="$1"
  local backup_id="$2"
  local token="$3"
  local want="${4:-succeeded}"
  local status="" i=0
  while (( i < 120 )); do
    status="$(
      api_get "/ponds/$pond_id/backups" "$token" \
        | py_json "
import sys, json
d=json.load(sys.stdin)
want='$backup_id'
for b in d.get('backups') or []:
  if b.get('id')==want:
    print(b.get('status') or '')
    break
" 2>/dev/null || true
    )"
    echo "  backup status=$status"
    [[ "$status" == "$want" ]] && return 0
    if [[ "$status" == "failed" ]]; then
      return 1
    fi
    sleep 2
    i=$((i + 2))
  done
  return 1
}

# Sets DEMO_JWT (stdout stays for humans; callers read the var).
seed_and_login() {
  info "make seed"
  local seed_try=0
  until DATABASE_URL="$DB_URL_HOST" make seed; do
    seed_try=$((seed_try + 1))
    if (( seed_try > 3 )); then
      die "seed falló. ¿users existe? corré migrate y logs api"
    fi
    warn "seed falló — reintento migrate + seed ($seed_try)"
    migrate_host_if_needed
    sleep 2
  done
  ok "Seed OK — $DEMO_EMAIL / $DEMO_PASSWORD"

  info "Login…"
  DEMO_JWT="$(login_token "$DEMO_EMAIL" "$DEMO_PASSWORD")"
  [[ -n "$DEMO_JWT" ]] || die "login sin access_token"
  ok "JWT OK"
}

# Sets DEMO_POND_ID for the created running pond.
create_running_pond() {
  local token="$1"
  local pond_name="$2"
  local pond_json pond_id

  info "POST /ponds ($pond_name)…"
  pond_json="$(api_post "/ponds" "{\"name\":\"$pond_name\"}" "$token")"
  echo "$pond_json" | python3 -m json.tool 2>/dev/null || echo "$pond_json"
  pond_id="$(echo "$pond_json" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or d.get('pond_id') or '')")"
  if [[ -z "$pond_id" ]]; then
    warn "POST /ponds sin id — reintento con nombre único"
    pond_name="${pond_name}-$(date +%s)"
    pond_json="$(api_post "/ponds" "{\"name\":\"$pond_name\"}" "$token")"
    echo "$pond_json" | python3 -m json.tool 2>/dev/null || echo "$pond_json"
    pond_id="$(echo "$pond_json" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or d.get('pond_id') or '')")"
  fi
  [[ -n "$pond_id" ]] || die "no pude leer pond id"

  info "Poll observed_state=running (pond $pond_id)…"
  poll_pond_running "$pond_id" "$token" \
    || die "pond no llegó a running. logs: ${COMPOSE_B[*]} logs node-agent --tail 80"
  DEMO_POND_ID="$pond_id"
}

start_control_plane() {
  ensure_docker
  need_cmd curl
  need_cmd python3
  [[ "${SKIP_GIT:-0}" == "1" ]] || ensure_git_main

  free_port 8000 "API"
  ensure_db_host_port

  info "Levantando db (probe de red) en host :${KOI_DB_HOST_PORT}…"
  AGENT_MODE=docker KOI_DB_HOST_PORT="$KOI_DB_HOST_PORT" "${COMPOSE_B[@]}" up --build -d db
  wait_tcp 127.0.0.1 "$KOI_DB_HOST_PORT" 45 || die "db no abre ${KOI_DB_HOST_PORT}"
  use_hostnet_overlay_if_needed
  info "Levantando api + node-agent (AGENT_MODE=docker)…"
  AGENT_MODE=docker KOI_DB_HOST_PORT="$KOI_DB_HOST_PORT" "${COMPOSE_B[@]}" up --build -d db api node-agent
  if ! wait_http "http://127.0.0.1:8000/api/v1/health" 180; then
    if ! wait_http "http://127.0.0.1:8000/health" 30; then
      die "API no healthy. Revisá: AGENT_MODE=docker ${COMPOSE_B[*]} logs api --tail 80"
    fi
  fi
  migrate_host_if_needed
}

ensure_git_main() {
  if [[ "${SKIP_GIT:-0}" == "1" ]]; then
    warn "SKIP_GIT=1 — no actualizo main"
    return 0
  fi
  need_cmd git
  info "Actualizando main…"
  git fetch origin main

  local cur
  cur="$(git branch --show-current 2>/dev/null || true)"
  if [[ "$cur" != "main" ]]; then
    if git worktree list | grep -qE '\[[[:space:]]*main[[:space:]]*\]|main$'; then
      # main checked out elsewhere — try to use this tree if already detached at main tip
      if git rev-parse HEAD | grep -q "$(git rev-parse origin/main)"; then
        warn "main está en otro worktree; HEAD ya apunta a origin/main"
      else
        warn "main está en otro worktree. Liberá con:"
        echo "  git worktree list"
        echo "  git worktree remove --force <path> || git worktree prune"
        echo "  git checkout main && git pull origin main"
        if git checkout main 2>/dev/null; then
          :
        else
          die "No pude checkout main (worktree). Liberá el worktree y reintentá."
        fi
      fi
    else
      git checkout main
    fi
  fi
  git pull origin main || die "git pull falló"
  local head
  head="$(git rev-parse --short HEAD)"
  ok "HEAD $head (esperamos ~969cf09 o más nuevo en main)"
}

cmd_preflight() {
  ensure_docker
  need_cmd curl
  need_cmd python3
  command -v psql >/dev/null 2>&1 && ok "psql OK" || warn "psql no está en PATH (Demo A lo necesita)"
  command -v uv >/dev/null 2>&1 && ok "uv OK" || warn "uv no está en PATH (seed host-side lo usa; API en Docker igual migra)"
  ensure_git_main
  echo
  info "Puertos:"
  for p in 15432 5432 8000; do
    if port_in_use "$p"; then
      warn "$p OCUPADO"
      lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null || true
      docker ps --filter publish="$p" --format '  docker: {{.ID}} {{.Names}} {{.Ports}}' 2>/dev/null || true
    else
      ok "$p libre"
    fi
  done
  echo
  ok "Preflight listo. Siguiente: $0 reset && $0 a   (o $0 all)"
}

cmd_reset() {
  ensure_docker
  info "Bajando stack Demo B…"
  AGENT_MODE=docker "${COMPOSE_B[@]}" down --remove-orphans 2>/dev/null || true
  docker compose --profile ponds down 2>/dev/null || true
  docker rm -f koicloud-inventario-demo 2>/dev/null || true
  # ponds creados por agent
  while read -r cid; do
    [[ -z "$cid" ]] && continue
    docker rm -f "$cid" 2>/dev/null || true
  done < <(docker ps -aq --filter label=koicloud.managed=true 2>/dev/null || true)
  while read -r cid; do
    [[ -z "$cid" ]] && continue
    docker rm -f "$cid" 2>/dev/null || true
  done < <(docker ps -aq --filter name=koicloud 2>/dev/null || true)
  free_port 15432 "pond-demo"
  free_port 8000 "API"
  # Prefer default 5432; remap happens in Demo B if host Postgres owns it.
  if port_in_use 5432; then
    warn "5432 ocupado (probable Postgres del host) — Demo B remapea a KOI_DB_HOST_PORT"
  else
    ok "compose db libre (5432)"
  fi
  ok "Reset limpio"
}

cmd_demo_a() {
  ensure_docker
  [[ "${SKIP_GIT:-0}" == "1" ]] || ensure_git_main
  free_port 15432 "pond-demo"
  info "make pond-demo"
  make pond-demo
  wait_tcp 127.0.0.1 15432 45 || die "pond-demo no abre 15432"
  # pg_isready dentro del container
  local i=0
  while (( i < 40 )); do
    if docker exec koicloud-inventario-demo pg_isready -U postgres -d inventario_demo >/dev/null 2>&1; then
      break
    fi
    sleep 1
    i=$((i + 1))
  done
  need_cmd psql
  # reconexión si el server corta la 1ª query (común al boot)
  info "Probando psql (reintento si corta)…"
  local try=0
  until psql "$POND_URI" -v ON_ERROR_STOP=1 -c 'SELECT version();' >/dev/null 2>&1; do
    try=$((try + 1))
    (( try > 15 )) && die "psql no conecta a pond-demo"
    sleep 1
  done
  ok "Demo A lista — pond en 15432"
  echo
  echo "Conectá con:"
  echo "  psql \"$POND_URI\""
  echo "O corré el SQL demo:"
  echo "  $0 sql"
}

cmd_sql() {
  need_cmd psql
  wait_tcp 127.0.0.1 15432 10 || die "pond-demo no está arriba — corré: $0 a"
  info "SQL inventario (idempotente-ish: DROP IF EXISTS)…"
  psql "$POND_URI" -v ON_ERROR_STOP=1 <<'SQL'
\conninfo
SELECT version();

DROP TABLE IF EXISTS inventario;
CREATE TABLE inventario (
  id          serial PRIMARY KEY,
  sku         text NOT NULL UNIQUE,
  producto    text NOT NULL,
  stock       int  NOT NULL CHECK (stock >= 0),
  actualizado timestamptz NOT NULL DEFAULT now()
);

INSERT INTO inventario (sku, producto, stock) VALUES
  ('KOI-001', 'Pond Micro', 12),
  ('KOI-002', 'Pond Starter', 5),
  ('KOI-003', 'Backup diario', 0);

SELECT id, sku, producto, stock, actualizado
FROM inventario
ORDER BY id;

UPDATE inventario SET stock = stock - 1 WHERE sku = 'KOI-001' RETURNING *;

SELECT count(*) AS filas, sum(stock) AS unidades
FROM inventario;
SQL
  ok "SQL demo OK — mostrale esto al ing"
}

migrate_host_if_needed() {
  info "Asegurando migraciones (host alembic, por si el API aún no migró)…"
  if ! command -v uv >/dev/null 2>&1; then
    warn "sin uv en host — confío en alembic del container api"
    return 0
  fi
  (
    cd apps/api
    DATABASE_URL="$DB_URL_HOST" uv run alembic upgrade head
  ) && ok "alembic upgrade head OK" || warn "alembic host falló — si seed falla, mirá logs del api"
}

# Pick a host publish port for compose `db`. Prefer 5432; if a host Postgres
# owns it (common: EnterpriseDB LaunchDaemon) and we cannot kill it, remap.
ensure_db_host_port() {
  local preferred="${KOI_DB_HOST_PORT:-5432}"
  local fallback="${KOI_DB_FALLBACK_PORT:-5433}"
  KOI_DB_HOST_PORT="$preferred"
  export KOI_DB_HOST_PORT

  if ! port_in_use "$preferred"; then
    ok "compose db libre ($preferred)"
  else
    warn "compose db ocupado ($preferred) — intentando liberar Docker…"
    # Docker-first free (no die): stop containers publishing the port
    local id
    for id in $(docker_ids_on_port "$preferred" | sort -u); do
      [[ -z "$id" ]] && continue
      info "docker stop $id"
      docker stop "$id" >/dev/null || true
    done
    sleep 1
    if port_in_use "$preferred" && [[ "${FORCE:-0}" == "1" ]]; then
      local pid
      for pid in $(port_pids "$preferred"); do
        warn "FORCE=1 → kill $pid (puerto $preferred)"
        kill "$pid" 2>/dev/null || true
        sleep 0.5
        kill -9 "$pid" 2>/dev/null || true
      done
      sleep 1
    fi
  fi

  if port_in_use "$preferred"; then
    if [[ "$preferred" == "$fallback" ]]; then
      die "Puerto $preferred sigue ocupado y no hay fallback. Liberá Postgres del host o set KOI_DB_HOST_PORT."
    fi
    warn "Puerto $preferred ocupado por Postgres del host (lsof puede no verlo) — publicando db en $fallback"
    KOI_DB_HOST_PORT="$fallback"
    export KOI_DB_HOST_PORT
    if port_in_use "$KOI_DB_HOST_PORT"; then
      die "Fallback $KOI_DB_HOST_PORT también ocupado"
    fi
    ok "db host port → $KOI_DB_HOST_PORT"
  fi

  DB_URL_HOST="postgresql+asyncpg://koi:koi@127.0.0.1:${KOI_DB_HOST_PORT}/koicloud"
  export DATABASE_URL="$DB_URL_HOST"
}

cmd_demo_b() {
  start_control_plane

  info "make seed"
  local seed_try=0
  until DATABASE_URL="$DB_URL_HOST" make seed; do
    seed_try=$((seed_try + 1))
    if (( seed_try > 3 )); then
      die "seed falló. ¿users existe? corré migrate y logs api"
    fi
    warn "seed falló — reintento migrate + seed ($seed_try)"
    migrate_host_if_needed
    sleep 2
  done
  ok "Seed OK — $DEMO_EMAIL / $DEMO_PASSWORD"

  info "Login…"
  local token
  token="$(
    curl -sS -X POST http://127.0.0.1:8000/api/v1/auth/login \
      -H 'Content-Type: application/json' \
      -d "{\"email\":\"$DEMO_EMAIL\",\"password\":\"$DEMO_PASSWORD\"}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])"
  )"
  [[ -n "$token" ]] || die "login sin access_token"
  ok "JWT OK"

  info "POST /ponds…"
  local pond_json pond_id
  pond_json="$(
    curl -sS -X POST http://127.0.0.1:8000/api/v1/ponds \
      -H "Authorization: Bearer $token" \
      -H 'Content-Type: application/json' \
      -d "{\"name\":\"$DEMO_POND_NAME\"}"
  )"
  echo "$pond_json" | python3 -m json.tool 2>/dev/null || echo "$pond_json"
  pond_id="$(echo "$pond_json" | python3 -c "import json,sys; d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or d.get('pond_id') or '')")"
  # If name taken / previous failed row, list and reuse a non-failed pond or create with suffix
  if [[ -z "$pond_id" ]]; then
    warn "POST /ponds sin id — reintento con nombre único"
    DEMO_POND_NAME="${DEMO_POND_NAME}-$(date +%s)"
    pond_json="$(
      curl -sS -X POST http://127.0.0.1:8000/api/v1/ponds \
        -H "Authorization: Bearer $token" \
        -H 'Content-Type: application/json' \
        -d "{\"name\":\"$DEMO_POND_NAME\"}"
    )"
    echo "$pond_json" | python3 -m json.tool 2>/dev/null || echo "$pond_json"
    pond_id="$(echo "$pond_json" | python3 -c "import json,sys; d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or d.get('pond_id') or '')")"
  fi
  [[ -n "$pond_id" ]] || die "no pude leer pond id de la respuesta"

  info "Poll observed_state=running (pond $pond_id)…"
  local state="" i=0
  while (( i < 90 )); do
    state="$(
      curl -sS "http://127.0.0.1:8000/api/v1/ponds/$pond_id" \
        -H "Authorization: Bearer $token" \
      | python3 -c "import json,sys; d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('observed_state') or d.get('status') or '')" 2>/dev/null || true
    )"
    echo "  state=$state"
    if [[ "$state" == "running" ]]; then
      break
    fi
    sleep 2
    i=$((i + 2))
  done
  [[ "$state" == "running" ]] || die "pond no llegó a running (último state=$state). logs: ${COMPOSE_B[*]} logs node-agent --tail 80"

  info "GET connection…"
  local conn
  conn="$(
    curl -sS "http://127.0.0.1:8000/api/v1/ponds/$pond_id/connection" \
      -H "Authorization: Bearer $token"
  )"
  echo "$conn" | python3 -m json.tool 2>/dev/null || echo "$conn"
  ok "Demo B lista"
  echo
  echo "Creds: $DEMO_EMAIL / $DEMO_PASSWORD"
  echo "TOKEN export (opcional):"
  echo "  export KOI_TOKEN=$token"
}

cmd_full() {
  start_control_plane

  local email="$FULL_DEMO_EMAIL"
  local password="$FULL_DEMO_PASSWORD"
  local pond_name="$FULL_DEMO_POND"

  info "POST /auth/register ($email)…"
  local reg_json
  reg_json="$(
    api_post "/auth/register" \
      "{\"email\":\"$email\",\"password\":\"$password\",\"full_name\":\"$FULL_DEMO_NAME\"}"
  )"
  echo "$reg_json" | python3 -m json.tool 2>/dev/null || echo "$reg_json"
  py_json "d=json.load(sys.stdin); assert d.get('email_verified') is False" <<<"$reg_json" \
    || die "register no devolvió email_verified:false"

  info "Extrayendo token de verificación de logs del api…"
  local verify_token
  verify_token="$(extract_verify_token "$email")"
  ok "verify token OK"

  info "POST /auth/verify…"
  local verify_json
  verify_json="$(api_post "/auth/verify" "{\"token\":\"$verify_token\"}")"
  echo "$verify_json" | python3 -m json.tool 2>/dev/null || echo "$verify_json"

  info "Login…"
  local token
  token="$(login_token "$email" "$password")"
  [[ -n "$token" ]] || die "login sin access_token"
  ok "JWT OK"

  info "GET /plans…"
  local plans_json
  plans_json="$(api_get "/plans")"
  echo "$plans_json" | python3 -m json.tool 2>/dev/null || echo "$plans_json"

  info "POST /subscriptions (plan micro)…"
  # G1 + W3-07: subscribe persiste subscription + invoice + payment (método simulated).
  local sub_json
  sub_json="$(api_post "/subscriptions" '{"plan_id":"micro"}' "$token")"
  echo "$sub_json" | python3 -m json.tool 2>/dev/null || echo "$sub_json"
  echo "$sub_json" | py_json "
d=json.load(sys.stdin)
inv=d.get('invoice') or {}
pay=d.get('payment') or {}
sub=d.get('subscription') or {}
assert sub.get('status')=='active', sub
assert inv.get('status')=='paid', inv
assert inv.get('number','').startswith('KC-'), inv
assert float(inv.get('iva_usd') or 0)>0, inv
assert pay.get('method')=='simulated', pay
print('subscribe OK', inv.get('number'), 'IVA', inv.get('iva_usd'))
" || die "subscribe no devolvió factura persistida con IVA (¿G1 en main?)"

  info "POST /ponds ($pond_name)…"
  local pond_json pond_id
  pond_json="$(api_post "/ponds" "{\"name\":\"$pond_name\"}" "$token")"
  echo "$pond_json" | python3 -m json.tool 2>/dev/null || echo "$pond_json"
  pond_id="$(echo "$pond_json" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or d.get('pond_id') or '')")"
  if [[ -z "$pond_id" ]]; then
    warn "nombre ocupado — reintento con sufijo"
    pond_name="${pond_name}-$(date +%s)"
    pond_json="$(api_post "/ponds" "{\"name\":\"$pond_name\"}" "$token")"
    echo "$pond_json" | python3 -m json.tool 2>/dev/null || echo "$pond_json"
    pond_id="$(echo "$pond_json" | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('id') or d.get('pond_id') or '')")"
  fi
  [[ -n "$pond_id" ]] || die "no pude leer pond id"

  info "Poll observed_state=running (pond $pond_id)…"
  poll_pond_running "$pond_id" "$token" || die "pond no llegó a running. logs: ${COMPOSE_B[*]} logs node-agent --tail 80"

  info "GET /ponds/$pond_id/connection…"
  local conn_json conn_uri
  conn_json="$(api_get "/ponds/$pond_id/connection" "$token")"
  echo "$conn_json" | python3 -m json.tool 2>/dev/null || echo "$conn_json"
  conn_uri="$(echo "$conn_json" | py_json "d=json.load(sys.stdin); c=d.get('connection') or d; print((c or {}).get('uri') or '')" 2>/dev/null || true)"

  if [[ -n "$conn_uri" ]] && command -v psql >/dev/null 2>&1; then
    info "psql CREATE TABLE items…"
    psql "$conn_uri" -v ON_ERROR_STOP=1 -c \
      'CREATE TABLE IF NOT EXISTS items(id serial PRIMARY KEY, nombre text);' \
      -c "INSERT INTO items(nombre) SELECT 'demo' WHERE NOT EXISTS (SELECT 1 FROM items LIMIT 1);" \
      -c 'SELECT * FROM items;' \
      && ok "psql OK" \
      || warn "psql falló — el pond igual está running; probá manual"
  else
    warn "sin psql o sin uri — saltando CREATE TABLE"
  fi

  info "Demo propose→confirm (DELETE pond vía superficie CLI)…"
  local del_json confirm_token
  del_json="$(curl -sS -X DELETE "${API_BASE}/ponds/$pond_id" \
    -H "Authorization: Bearer $token" \
    -H 'X-KOI-Surface: cli')"
  echo "$del_json" | python3 -m json.tool 2>/dev/null || echo "$del_json"
  confirm_token="$(echo "$del_json" | py_json "d=json.load(sys.stdin); print(d.get('token') or '')" 2>/dev/null || true)"
  if [[ -n "$confirm_token" ]]; then
    echo "$del_json" | py_json "print('Summary:', json.load(sys.stdin).get('summary',''))" 2>/dev/null || true
    if [[ "${DEMO_CONFIRM_DELETE:-0}" == "1" ]]; then
      info "POST /confirm/$confirm_token…"
      api_post "/confirm/$confirm_token" '{}' "$token" | python3 -m json.tool 2>/dev/null || true
      ok "confirm OK — pond en deleting"
    else
      warn "DEMO_CONFIRM_DELETE=0 — dejé el pond running para la Web. Para confirmar: curl -X POST ${API_BASE}/confirm/$confirm_token -H \"Authorization: Bearer \$KOI_TOKEN\""
    fi
  else
    warn "no hubo confirmation_required en delete"
  fi

  ok "Demo full lista"
  echo
  echo "Cuenta: $email / $password"
  echo "Pond:   $pond_name (id $pond_id)"
  echo "Web:    http://127.0.0.1:5173 (si levantaste apps/web con pnpm dev)"
  echo "Guion presentación: docs/runbooks/demo-vivo.md § Entrega final"
}

cmd_entrega() {
  cmd_reset
  SKIP_GIT=1 cmd_full
}

cmd_s3() {
  # S3 happy path (API real): subscribe → usage → invoice PDF+IVA → backup → restore
  start_control_plane

  seed_and_login
  local token="$DEMO_JWT"

  info "GET /plans…"
  local plans_json
  plans_json="$(api_get "/plans")"
  echo "$plans_json" | python3 -m json.tool 2>/dev/null || echo "$plans_json"
  echo "$plans_json" | py_json "
d=json.load(sys.stdin)
ids=[p.get('id') for p in (d.get('plans') or [])]
assert 'micro' in ids, ids
print('plans OK:', ', '.join(ids))
" || die "GET /plans sin plan micro"

  info "POST /subscriptions (plan micro) — API real (G1)…"
  local sub_json invoice_id invoice_number iva_usd payment_method
  sub_json="$(api_post "/subscriptions" '{"plan_id":"micro"}' "$token")"
  echo "$sub_json" | python3 -m json.tool 2>/dev/null || echo "$sub_json"
  eval "$(
    echo "$sub_json" | py_json "
d=json.load(sys.stdin)
inv=d.get('invoice') or {}
pay=d.get('payment') or {}
sub=d.get('subscription') or {}
assert sub.get('status')=='active', sub
assert inv.get('status')=='paid', inv
assert inv.get('number','').startswith('KC-'), inv
assert float(inv.get('iva_usd') or 0)>0, inv
assert float(inv.get('subtotal_usd') or 0)>0, inv
assert abs(float(inv['subtotal_usd'])+float(inv['iva_usd'])-float(inv['total_usd']))<1e-6, inv
assert pay.get('status')=='succeeded', pay
assert pay.get('method')=='simulated', pay
print(f\"invoice_id={inv['id']!r}\")
print(f\"invoice_number={inv['number']!r}\")
print(f\"iva_usd={inv['iva_usd']!r}\")
print(f\"payment_method={pay['method']!r}\")
"
  )" || die "subscribe no persistió invoice/payment con IVA"
  ok "Subscribe persistido — $invoice_number (IVA \$$iva_usd)"
  warn "Honestidad: payment.method=$payment_method (SimulatedPaymentProvider). Invoice/sub/PDF son filas reales, no fixture JSON."

  info "GET /usage…"
  local usage_json
  usage_json="$(api_get "/usage" "$token")"
  echo "$usage_json" | python3 -m json.tool 2>/dev/null || echo "$usage_json"
  echo "$usage_json" | py_json "
d=json.load(sys.stdin)
assert 'month' in d and 'total_instance_hours' in d and 'ponds' in d, d
hours=float(d.get('total_instance_hours') or 0)
print('usage month=', d.get('month'), 'instance_hours=', hours, 'ponds=', len(d.get('ponds') or []))
" || die "GET /usage no devolvió shape real"
  # Ceros son respuesta real (sin samples+aggregate); no es fixture.
  if echo "$usage_json" | py_json "d=json.load(sys.stdin); raise SystemExit(0 if float(d.get('total_instance_hours') or 0)==0 else 1)"; then
    warn "Honestidad: usage en 0 — endpoint real; falta pond_samples + daily_usage para horas > 0 en este ensayo fresco."
  else
    ok "Usage con horas > 0 (metering agregado)"
  fi

  info "GET /invoices/$invoice_id (JSON) + /pdf…"
  local inv_detail
  inv_detail="$(api_get "/invoices/$invoice_id" "$token")"
  echo "$inv_detail" | python3 -m json.tool 2>/dev/null || echo "$inv_detail"
  echo "$inv_detail" | py_json "
d=json.load(sys.stdin)
inv=d.get('invoice') or d
assert (inv or {}).get('id')=='$invoice_id', inv
assert (inv or {}).get('number')=='$invoice_number', inv
assert float((inv or {}).get('iva_usd') or 0)>0, inv
assert (inv or {}).get('status')=='paid', inv
print('invoice detail OK', inv.get('number'), 'IVA', inv.get('iva_usd'))
" || die "GET /invoices/{id} no coincide con subscribe"

  local pdf_path
  pdf_path="${S3_PDF_PATH:-/tmp/koicloud-s3-invoice.pdf}"
  mkdir -p "$(dirname "$pdf_path")"
  local http_code
  http_code="$(
    curl -sS -o "$pdf_path" -w '%{http_code}' \
      "${API_BASE}/invoices/${invoice_id}/pdf" \
      -H "Authorization: Bearer $token"
  )"
  [[ "$http_code" == "200" ]] || die "PDF HTTP $http_code (esperaba 200)"
  # Extract text from content streams (FlateDecode-safe). Do NOT latin-1-grep raw bytes.
  # Cross-check markers against invoice JSON (W3-10 renderer writes IVA 12 % + KC- code).
  python3 - "$pdf_path" "$invoice_number" <<'PY' || die "PDF inválido o sin IVA en texto extraído"
import re, sys, zlib
from pathlib import Path

path = Path(sys.argv[1])
want_number = sys.argv[2]
data = path.read_bytes()
assert data.startswith(b"%PDF"), data[:20]
assert len(data) > 1024, len(data)

def extract_pdf_text(raw: bytes) -> str:
    chunks: list[str] = []
    # Prefer pdftotext when present (poppler).
    import shutil, subprocess
    if shutil.which("pdftotext"):
        try:
            out = subprocess.check_output(
                ["pdftotext", "-layout", str(path), "-"],
                stderr=subprocess.DEVNULL,
            )
            if out.strip():
                return out.decode("utf-8", errors="ignore")
        except Exception:
            pass
    # Decode page content streams; inflate FlateDecode when needed.
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        body = m.group(1)
        # Heuristic: stream dict immediately precedes; look back for /FlateDecode.
        start = m.start()
        header = raw[max(0, start - 200) : start]
        candidates = [body]
        if b"/FlateDecode" in header:
            try:
                candidates.insert(0, zlib.decompress(body))
            except Exception:
                pass
        for cand in candidates:
            try:
                chunks.append(cand.decode("latin-1", errors="ignore"))
            except Exception:
                continue
    if chunks:
        return "\n".join(chunks)
    # Last resort (W3-10 sets compression=False today): uncompressed literals.
    return raw.decode("latin-1", errors="ignore")

text = extract_pdf_text(data)
assert "IVA" in text, "missing IVA in extracted PDF text"
assert "12" in text, "missing 12% marker in extracted PDF text"
assert want_number in text or "KC-" in text, (want_number, text[:400])
print(f"pdf OK bytes={len(data)} path={path} number={want_number}")
PY
  ok "Invoice PDF con IVA → $pdf_path"

  local pond_name="${S3_DEMO_POND:-s3-demo}"
  create_running_pond "$token" "$pond_name"
  local pond_id="$DEMO_POND_ID"

  info "GET /ponds/$pond_id/connection + seed SQL (para restore visible)…"
  local conn_json conn_uri
  conn_json="$(api_get "/ponds/$pond_id/connection" "$token")"
  echo "$conn_json" | python3 -m json.tool 2>/dev/null || echo "$conn_json"
  conn_uri="$(echo "$conn_json" | py_json "d=json.load(sys.stdin); c=d.get('connection') or d; print((c or {}).get('uri') or '')" 2>/dev/null || true)"
  if [[ -n "$conn_uri" ]] && command -v psql >/dev/null 2>&1; then
    psql "$conn_uri" -v ON_ERROR_STOP=1 -c \
      'CREATE TABLE IF NOT EXISTS s3_demo(id serial PRIMARY KEY, nota text);' \
      -c "INSERT INTO s3_demo(nota) VALUES ('pre-backup');" \
      -c 'SELECT * FROM s3_demo;' \
      && ok "SQL pre-backup OK" \
      || warn "psql pre-backup falló — sigo con backup igual"
  else
    warn "sin psql o sin uri — backup/restore igual corren; no hay fila SQL de contraste"
  fi

  info "POST /ponds/$pond_id/backups…"
  local backup_json backup_id
  backup_json="$(api_post "/ponds/$pond_id/backups" '{}' "$token")"
  echo "$backup_json" | python3 -m json.tool 2>/dev/null || echo "$backup_json"
  backup_id="$(echo "$backup_json" | py_json "d=json.load(sys.stdin); b=d.get('backup') or {}; print(b.get('id') or '')")"
  [[ -n "$backup_id" ]] || die "trigger_backup sin backup.id"
  info "Poll backup succeeded ($backup_id)…"
  poll_backup_status "$pond_id" "$backup_id" "$token" succeeded \
    || die "backup no llegó a succeeded. logs: ${COMPOSE_B[*]} logs node-agent --tail 80"
  ok "Backup succeeded — $backup_id"

  if [[ -n "$conn_uri" ]] && command -v psql >/dev/null 2>&1; then
    info "Mutación post-backup (INSERT post-backup)…"
    psql "$conn_uri" -v ON_ERROR_STOP=1 -c \
      "INSERT INTO s3_demo(nota) VALUES ('post-backup-should-vanish');" \
      -c 'SELECT * FROM s3_demo ORDER BY id;' \
      || warn "mutación post-backup falló"
  fi

  local restore_at_before
  restore_at_before="$(
    api_get "/ponds/$pond_id" "$token" \
      | py_json "d=json.load(sys.stdin); p=d.get('pond') if isinstance(d.get('pond'), dict) else d; print((p or {}).get('last_restore_at') or '')" \
      2>/dev/null || true
  )"

  info "POST /ponds/$pond_id/restore…"
  local restore_json
  restore_json="$(api_post "/ponds/$pond_id/restore" "{\"backup_id\":\"$backup_id\"}" "$token")"
  echo "$restore_json" | python3 -m json.tool 2>/dev/null || echo "$restore_json"
  echo "$restore_json" | py_json "
d=json.load(sys.stdin)
job=d.get('job') or d
assert (job or {}).get('type')=='restore_pond', d
assert (job or {}).get('status') in ('queued','running','succeeded'), d
print('restore job', (job or {}).get('id'), (job or {}).get('status'))
" || die "restore no encoló restore_pond"

  info "Poll restore complete (last_restore_at cambia + observed=running)…"
  local state="" restore_at="" i=0 saw_restoring=0
  while (( i < 120 )); do
    eval "$(
      api_get "/ponds/$pond_id" "$token" | py_json "
d=json.load(sys.stdin)
p=d.get('pond') if isinstance(d.get('pond'), dict) else d
p=p or {}
print('state=%r' % (p.get('observed_state') or ''))
print('restore_at=%r' % (p.get('last_restore_at') or ''))
" 2>/dev/null || echo "state=''; restore_at=''"
    )"
    echo "  state=$state last_restore_at=$restore_at"
    [[ "$state" == "restoring" ]] && saw_restoring=1
    if [[ -n "$restore_at" && "$restore_at" != "$restore_at_before" && "$state" == "running" ]]; then
      break
    fi
    # Fallback: saw restoring then running (si last_restore_at no se setea en algún build)
    if (( saw_restoring == 1 )) && [[ "$state" == "running" ]]; then
      break
    fi
    sleep 2
    i=$((i + 2))
  done
  if [[ "$state" != "running" ]]; then
    die "pond no volvió a running tras restore (último=$state)"
  fi
  ok "Restore completo — pond running"

  if [[ -n "$conn_uri" ]] && command -v psql >/dev/null 2>&1; then
    info "Verificando SQL post-restore (solo pre-backup)…"
    psql "$conn_uri" -v ON_ERROR_STOP=1 -c 'SELECT * FROM s3_demo ORDER BY id;' \
      && ok "SQL post-restore OK" \
      || warn "psql post-restore falló — revisá URI/conexión"
  fi

  ok "S3 happy path listo"
  echo
  echo "Creds:   $DEMO_EMAIL / $DEMO_PASSWORD"
  echo "Invoice: $invoice_number  PDF: $pdf_path"
  echo "Pond:    $pond_id  Backup: $backup_id"
  echo "TOKEN:   export KOI_TOKEN=$token"
  echo
  echo "Gaps honestos:"
  echo "  - payment.method=simulated (port real SimulatedPaymentProvider; no tarjeta)"
  echo "  - usage puede ir en 0 en ensayo fresco (API real; falta aggregate diario)"
  echo "  - backup/restore dependen de AGENT_MODE=docker + node-agent (este script lo levanta)"
}

cmd_s3_entrega() {
  cmd_reset
  SKIP_GIT=1 cmd_s3
}

cmd_warm() {
  SKIP_GIT="${SKIP_GIT:-0}" cmd_demo_a
  ok "Pond caliente. En la talk: psql + $0 sql"
}

cmd_all() {
  cmd_reset
  SKIP_GIT=1 cmd_demo_a
  echo
  info "=== Demo A OK — Ctrl+C si solo querés A; en 3s sigo a B ==="
  sleep 3
  SKIP_GIT=1 cmd_demo_b
  echo
  ok "ALL listo. Narrá A (sql) y después B (API ya seeded)."
}

usage() {
  cat <<EOF
KoiCloud demo vivo

  $(basename "$0") preflight   # docker, git, puertos
  $(basename "$0") reset       # baja compose/ponds y libera 15432/5432/8000
  $(basename "$0") a           # Demo A (pond-demo)
  $(basename "$0") sql         # CREATE/INSERT/SELECT inventario
  $(basename "$0") b           # Demo B (compose + migrate + seed + pond)
  $(basename "$0") full        # register → Micro → pond + confirm (API)
  $(basename "$0") entrega     # reset → full
  $(basename "$0") s3          # S3: subscribe → usage → PDF+IVA → backup → restore
  $(basename "$0") s3-entrega  # reset → s3
  $(basename "$0") warm        # deja A lista
  $(basename "$0") all         # reset → A → B

  FORCE=1 $(basename "$0") reset   # mata PIDs que bloquean puertos
  SKIP_GIT=1 $(basename "$0") a    # sin pull

Antes de entrar al aula:
  $(basename "$0") preflight && $(basename "$0") all

S3 (Avance 50 %):
  $(basename "$0") preflight && $(basename "$0") s3-entrega
EOF
}

main() {
  find_root
  info "Repo: $(pwd)"
  local cmd="${1:-}"
  case "$cmd" in
    preflight|pf) cmd_preflight ;;
    reset|clean)  cmd_reset ;;
    a|A|demo-a)   cmd_demo_a ;;
    sql|SQL)      cmd_sql ;;
    b|B|demo-b)   cmd_demo_b ;;
    full|entrega-final|f) cmd_full ;;
    entrega|e)    cmd_entrega ;;
    s3|S3)        cmd_s3 ;;
    s3-entrega|s3e) cmd_s3_entrega ;;
    warm)         cmd_warm ;;
    all)          cmd_all ;;
    -h|--help|help|"") usage ;;
    *) die "comando desconocido: $cmd (help)" ;;
  esac
}

main "$@"
