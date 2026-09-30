#!/usr/bin/env bash
# KoiCloud — demo en vivo a prueba de fallos (Mac/Linux + Docker)
# Uso (desde el clone, o con KOICLOUD_ROOT):
#   bash path/to/demo-vivo.sh preflight
#   bash path/to/demo-vivo.sh reset
#   bash path/to/demo-vivo.sh a          # Demo A (siempre)
#   bash path/to/demo-vivo.sh b          # Demo B (control plane)
#   bash path/to/demo-vivo.sh all        # reset → A → B
#   bash path/to/demo-vivo.sh sql        # solo SQL inventario en pond-demo
#   bash path/to/demo-vivo.sh warm       # deja A caliente sin SQL
#
# Flags:
#   FORCE=1   mata el proceso que escucha el puerto (último recurso)
#   SKIP_GIT=1  no hace pull
#
# Creds Demo B (post-seed): demo@koicloud.dev / Sup3rSegura!2026

set -euo pipefail

DEMO_EMAIL="${DEMO_EMAIL:-demo@koicloud.dev}"
DEMO_PASSWORD="${DEMO_PASSWORD:-Sup3rSegura!2026}"
POND_URI="${POND_URI:-postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo}"
DB_URL_HOST="${DATABASE_URL:-postgresql+asyncpg://koi:koi@127.0.0.1:5432/koicloud}"
COMPOSE_B=(docker compose -f docker-compose.yml -f docker-compose.docker-agent.yml)

use_hostnet_overlay_if_needed() {
  [[ "${FORCE_HOSTNET:-0}" == "1" ]] || {
    # After db is up, probe container→db. Failure ⇒ hostnet overlay (cloud VM quirk).
    local net
    net="$(docker network ls --format '{{.Name}}' | grep -E 'koicloud_default|_default$' | head -1 || true)"
    [[ -n "$net" ]] || return 0
    if docker run --rm --network "$net" postgres:16-alpine \
        pg_isready -h db -U koi -d koicloud >/dev/null 2>&1; then
      return 0
    fi
  }
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

port_in_use() {
  local port="$1"
  local pids
  pids="$(port_pids "$port")"
  [[ -n "$pids" ]]
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
  info "Esperando $host:$port…"
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
  free_port 5432 "compose db"
  free_port 8000 "API"
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

cmd_demo_b() {
  ensure_docker
  need_cmd curl
  need_cmd python3
  [[ "${SKIP_GIT:-0}" == "1" ]] || ensure_git_main

  free_port 5432 "compose db"
  free_port 8000 "API"

  info "Levantando db (probe de red)…"
  AGENT_MODE=docker "${COMPOSE_B[@]}" up --build -d db
  wait_tcp 127.0.0.1 5432 45 || die "db no abre 5432"
  use_hostnet_overlay_if_needed
  info "Levantando api + node-agent (AGENT_MODE=docker)…"
  AGENT_MODE=docker "${COMPOSE_B[@]}" up --build -d db api node-agent
  # API tarda: uv sync + alembic + uvicorn
  if ! wait_http "http://127.0.0.1:8000/api/v1/health" 180; then
    if ! wait_http "http://127.0.0.1:8000/health" 30; then
      die "API no healthy. Revisá: AGENT_MODE=docker ${COMPOSE_B[*]} logs api --tail 80"
    fi
  fi

  migrate_host_if_needed

  info "make seed"
  local seed_try=0
  until make seed; do
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
      -d '{"name":"inventario-demo"}'
  )"
  echo "$pond_json" | python3 -m json.tool 2>/dev/null || echo "$pond_json"
  pond_id="$(echo "$pond_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id') or d.get('pond_id') or '')")"
  [[ -n "$pond_id" ]] || die "no pude leer pond id de la respuesta"

  info "Poll observed_state=running (pond $pond_id)…"
  local state="" i=0
  while (( i < 90 )); do
    state="$(
      curl -sS "http://127.0.0.1:8000/api/v1/ponds/$pond_id" \
        -H "Authorization: Bearer $token" \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('observed_state') or d.get('status') or '')" 2>/dev/null || true
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
  $(basename "$0") warm        # deja A lista
  $(basename "$0") all         # reset → A → B

  FORCE=1 $(basename "$0") reset   # mata PIDs que bloquean puertos
  SKIP_GIT=1 $(basename "$0") a    # sin pull

Antes de entrar al aula:
  $(basename "$0") preflight && $(basename "$0") all
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
    warm)         cmd_warm ;;
    all)          cmd_all ;;
    -h|--help|help|"") usage ;;
    *) die "comando desconocido: $cmd (help)" ;;
  esac
}

main "$@"
