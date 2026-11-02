#!/usr/bin/env bash
# /app/* reloads must return app.html, and the worker healthcheck must run
# on the worker base image without pgrep.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

FAILS=()
note_fail() {
  echo "FAIL: $*" >&2
  FAILS+=("$*")
}

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif sudo -n docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
else
  DOCKER=()
fi

python3 - "$ROOT" <<'PY' || note_fail "Caddyfile handle /app* is missing or incomplete"
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
errors: list[str] = []
for rel in ("infra/Caddyfile", "infra/Caddyfile.http"):
    text = (root / rel).read_text(encoding="utf-8")
    if "handle /api/*" not in text:
        errors.append(f"{rel}: missing handle /api/*")
    if "try_files {path} /index.html" not in text:
        errors.append(f"{rel}: landing fallback must stay try_files {{path}} /index.html")
    match = re.search(r"(?ms)^[ \t]*handle /app\* \{.*?^[ \t]*\}", text)
    if match is None:
        errors.append(f"{rel}: missing handle /app* block")
        continue
    block = match.group(0)
    if "try_files {path} /app.html" not in block:
        errors.append(f"{rel}: handle /app* must try_files {{path}} /app.html")
    if "file_server" not in block:
        errors.append(f"{rel}: handle /app* must file_server so real assets still serve")
    if "/srv/koicloud/web" not in block:
        errors.append(f"{rel}: handle /app* must root /srv/koicloud/web")
if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print("Caddyfiles declare handle /app* with try_files {path} /app.html")
PY

HC_JSON="$(python3 - "$ROOT" <<'PY'
import ast
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
compose = (root / "infra/docker-compose.prod.yml").read_text(encoding="utf-8")
lines = compose.splitlines()
start = None
for index, line in enumerate(lines):
    if line.startswith("  worker:"):
        start = index + 1
        break
if start is None:
    raise SystemExit("worker service missing from infra/docker-compose.prod.yml")
body: list[str] = []
for line in lines[start:]:
    if line.startswith("  ") and not line.startswith("   ") and line.strip():
        break
    body.append(line)
block = "\n".join(body)
marker = "\n    healthcheck:"
hc_at = block.find(marker)
if hc_at < 0:
    raise SystemExit("worker service has no healthcheck")
hc = block[hc_at:]
test_at = hc.find("test:")
if test_at < 0:
    raise SystemExit("worker healthcheck has no test")
rest = hc[test_at + len("test:"):]
open_at = rest.find("[")
if open_at < 0:
    raise SystemExit("worker healthcheck test is not a list")
depth = 0
end = None
for index, char in enumerate(rest[open_at:], open_at):
    if char == "[":
        depth += 1
    elif char == "]":
        depth -= 1
        if depth == 0:
            end = index + 1
            break
if end is None:
    raise SystemExit("worker healthcheck test list is unterminated")
argv = ast.literal_eval(rest[open_at:end])
if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
    raise SystemExit("worker healthcheck test must be a list of strings")
dockerfile = (root / "apps/api/Dockerfile").read_text(encoding="utf-8")
image = re.search(r"(?m)^FROM\s+(\S+)", dockerfile)
if image is None:
    raise SystemExit("apps/api/Dockerfile has no FROM")
print(json.dumps({"argv": argv, "image": image.group(1)}))
PY
)" || note_fail "could not read the worker healthcheck"

if [[ -n "${HC_JSON:-}" ]]; then
  echo "worker healthcheck: $HC_JSON"
fi

if [[ ${#DOCKER[@]} -eq 0 ]]; then
  note_fail "docker is not available. Install Docker to run caddy and the worker healthcheck."
else
  FIX="$(mktemp -d)"
  CADDY_NAME="koi-caddy-spa-$$"
  POS_NAME="koi-worker-pos-$$"
  NEG_NAME="koi-worker-neg-$$"
  cleanup() {
    "${DOCKER[@]}" rm -f "$CADDY_NAME" "$POS_NAME" "$NEG_NAME" >/dev/null 2>&1 || true
    rm -rf "$FIX"
  }
  trap cleanup EXIT

  mkdir -p "$FIX/web/assets" "$FIX/web/app/ponds"
  printf 'LANDING\n' >"$FIX/web/index.html"
  printf 'SPA_SHELL\n' >"$FIX/web/app.html"
  printf 'ASSET\n' >"$FIX/web/assets/mark.js"
  printf 'REAL_FILE\n' >"$FIX/web/app/ponds/real.txt"

  echo "===== caddy validate infra/Caddyfile ====="
  if ! "${DOCKER[@]}" run --rm --entrypoint caddy \
    -e KOICLOUD_DOMAIN=koicloud.example \
    -v "$ROOT/infra/Caddyfile:/etc/caddy/Caddyfile:ro" \
    caddy:2.8-alpine \
    validate --config /etc/caddy/Caddyfile --adapter caddyfile
  then
    note_fail "caddy validate failed for infra/Caddyfile"
  fi

  echo "===== caddy validate infra/Caddyfile.http ====="
  if ! "${DOCKER[@]}" run --rm --entrypoint caddy \
    -v "$ROOT/infra/Caddyfile.http:/etc/caddy/Caddyfile:ro" \
    caddy:2.8-alpine \
    validate --config /etc/caddy/Caddyfile --adapter caddyfile
  then
    note_fail "caddy validate failed for infra/Caddyfile.http"
  fi

  PORT="$(python3 - <<'PY'
import socket
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
)"
  if ! "${DOCKER[@]}" run -d --name "$CADDY_NAME" \
    -p "127.0.0.1:${PORT}:80" \
    -v "$ROOT/infra/Caddyfile.http:/etc/caddy/Caddyfile:ro" \
    -v "$FIX/web:/srv/koicloud/web:ro" \
    caddy:2.8-alpine >/dev/null
  then
    note_fail "caddy did not start with infra/Caddyfile.http"
  else
    ready=0
    for _ in $(seq 1 50); do
      if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/assets/mark.js"; then
        ready=1
        break
      fi
      sleep 0.1
    done
    if [[ "$ready" -ne 1 ]]; then
      "${DOCKER[@]}" logs "$CADDY_NAME" >&2 || true
      note_fail "caddy did not serve the fixture site"
    else
      expect_body() {
        local path="$1"
        local want="$2"
        local out="$FIX/body"
        local code
        code="$(curl -sS -o "$out" -w '%{http_code}' "http://127.0.0.1:${PORT}${path}")"
        local got
        got="$(cat "$out")"
        if [[ "$code" != "200" || "$got" != "$want" ]]; then
          note_fail "GET ${path} status=${code} body=$(printf %q "$got") want 200 $(printf %q "$want")"
        else
          echo "GET ${path} 200 $(printf %q "$want")"
        fi
      }
      expect_body "/app/ponds/x" "SPA_SHELL"
      expect_body "/app/ponds/x?tab=1" "SPA_SHELL"
      expect_body "/app/ponds/real.txt" "REAL_FILE"
      expect_body "/assets/mark.js" "ASSET"
      expect_body "/" "LANDING"
      api_code="$(curl -sS -o "$FIX/api-body" -w '%{http_code}' "http://127.0.0.1:${PORT}/api/v1/health" || true)"
      api_body="$(cat "$FIX/api-body")"
      if [[ "$api_code" == "200" || "$api_body" == "SPA_SHELL" || "$api_body" == "LANDING" ]]; then
        note_fail "GET /api/v1/health was served as the site (status=${api_code})"
      else
        echo "GET /api/v1/health status=${api_code} (proxied, not the SPA)"
      fi
    fi
  fi

  if [[ -n "${HC_JSON:-}" ]]; then
    IMAGE="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["image"])' <<<"$HC_JSON")"
    run_hc() {
      local name="$1"
      python3 - "$name" "$HC_JSON" "${DOCKER[@]}" <<'PY'
import json
import subprocess
import sys

name = sys.argv[1]
spec = json.loads(sys.argv[2])
docker = sys.argv[3:]
argv = spec["argv"]
kind = argv[0]
if kind == "CMD-SHELL":
    cmd = docker + ["exec", name, "sh", "-c", argv[1]]
elif kind == "CMD":
    cmd = docker + ["exec", name, *argv[1:]]
else:
    print(f"FAIL: unsupported healthcheck form {kind}", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(subprocess.call(cmd))
PY
    }

    "${DOCKER[@]}" run -d --name "$POS_NAME" --entrypoint sh "$IMAGE" \
      -c 'while true; do python -m app.workers.daily_backups; sleep 3600; done' >/dev/null
    set +e
    run_hc "$POS_NAME"
    pos_rc=$?
    set -e
    if [[ "$pos_rc" -ne 0 ]]; then
      note_fail "worker healthcheck exited ${pos_rc} while pid 1 cmdline contains app.workers (image ${IMAGE})"
    else
      echo "worker healthcheck passed on ${IMAGE} with app.workers in pid 1 cmdline"
    fi

    "${DOCKER[@]}" run -d --name "$NEG_NAME" --entrypoint sh "$IMAGE" -c 'sleep 3600' >/dev/null
    set +e
    run_hc "$NEG_NAME"
    neg_rc=$?
    set -e
    if [[ "$neg_rc" -eq 0 ]]; then
      note_fail "worker healthcheck exited 0 for a pid 1 that is not the worker"
    else
      echo "worker healthcheck rejected a non-worker pid 1 (exit ${neg_rc})"
    fi
  fi
fi

if [[ ${#FAILS[@]} -gt 0 ]]; then
  echo "check-caddy-spa-worker: ${#FAILS[@]} failure(s)" >&2
  exit 1
fi
echo "caddy spa reload + worker healthcheck OK"
