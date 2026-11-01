#!/usr/bin/env bash
# Validates infra/docker-compose.prod.yml without contacting a host.
# Also proves EMAIL_PROVIDER=console is rejected before traffic under prod.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE="${DOCKER_COMPOSE:-}"
if [[ -z "$COMPOSE" ]]; then
  if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
  else
    echo "docker compose is required for this check" >&2
    exit 1
  fi
fi

# Names-only example must not be fed to compose (empty overrides defaults).
# Happy path uses a non-console provider — console must not reach prod apply.
# Override KOI_CHECK_EMAIL_PROVIDER=console only to prove the check refuses it.
CHECK_EMAIL_PROVIDER="${KOI_CHECK_EMAIL_PROVIDER:-resend}"
CHECK_ENV="$(mktemp)"
BAD_CONSOLE_ENV="$(mktemp)"
UNSET_ENV="$(mktemp)"
trap 'rm -f "$CHECK_ENV" "$BAD_CONSOLE_ENV" "$UNSET_ENV"' EXIT
# Happy-path values are fixtures that do not start with change-me.
cat >"$CHECK_ENV" <<EOF
POSTGRES_USER=koi
POSTGRES_PASSWORD=gate-fixture-db-password
POSTGRES_DB=koicloud
DATABASE_URL=postgresql+asyncpg://koi:gate-fixture-db-password@db:5432/koicloud
JWT_SECRET=gate-fixture-jwt-secret-32bytes
REFRESH_TTL_DAYS=30
POND_PASSWORD_KEY=gate-fixture-fernet-key-not-default==
AGENT_MODE=docker
NODE_ID=node-prod
NODE_TOKEN=gate-fixture-node-token
KOICLOUD_DOMAIN=koicloud.example
NODE_PUBLIC_HOST=db.gate-fixture.example
POND_PORT_RANGE_START=15000
POND_PORT_RANGE_END=15999
MCP_ENABLED=true
MCP_DEMO_PASSWORD=gate-fixture-mcp-demo
EMAIL_PROVIDER=${CHECK_EMAIL_PROVIDER}
PAYMENT_PROVIDER=simulated
INVOICE_DIR=/var/lib/koicloud/invoices
BACKUP_DIR=/var/lib/koicloud/backups
INTERNAL_API_URL=http://127.0.0.1:8000/internal/v1
EOF

$COMPOSE --env-file "$CHECK_ENV" \
  -f "$ROOT/infra/docker-compose.prod.yml" config >/tmp/koicloud-prod-compose.yml

$COMPOSE --env-file "$CHECK_ENV" \
  -f "$ROOT/infra/docker-compose.prod.yml" \
  -f "$ROOT/infra/docker-compose.http.yml" config >/tmp/koicloud-http-compose.yml

set +e
python3 - <<'PY'
import re
from pathlib import Path

def service_block(src: str, service: str) -> str:
    lines = src.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.startswith(f"  {service}:"):
            start = index + 1
            break
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("  ") and not line.startswith("   ") and line.strip():
            break
        body.append(line)
    return "\n".join(body)


def env_assignments(block: str) -> dict[str, list[str]]:
    assignments: dict[str, list[str]] = {}
    in_env = False
    for line in block.splitlines():
        if line.startswith("    environment:"):
            in_env = True
            continue
        if not in_env:
            continue
        if line.startswith("    ") and not line.startswith("     ") and line.strip():
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        assignments.setdefault(key.strip(), []).append(value.strip())
    return assignments


def uses_required_env(value: str, key: str) -> bool:
    raw = value.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        raw = raw[1:-1]
    return raw.startswith("${" + key + ":?") and raw.endswith("}")


# Service env keys that must fail interpolation when the variable is unset.
REQUIRED_COMPOSE_ENV = (
    ("db", "POSTGRES_PASSWORD"),
    ("api", "DATABASE_URL"),
    ("api", "JWT_SECRET"),
    ("api", "NODE_TOKEN"),
    ("api", "POND_PASSWORD_KEY"),
    ("api", "MCP_DEMO_PASSWORD"),
    ("worker", "DATABASE_URL"),
    ("worker", "JWT_SECRET"),
    ("worker", "NODE_TOKEN"),
    ("worker", "POND_PASSWORD_KEY"),
)

SECURITY_HEADERS = (
    ("Strict-Transport-Security", None),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", None),
    ("X-Frame-Options", "DENY"),
)

text = Path("/tmp/koicloud-prod-compose.yml").read_text(encoding="utf-8")
http = Path("/tmp/koicloud-http-compose.yml").read_text(encoding="utf-8")
caddy = Path("infra/Caddyfile").read_text(encoding="utf-8")
caddy_http = Path("infra/Caddyfile.http").read_text(encoding="utf-8")
env_names = Path("infra/.env.production.example").read_text(encoding="utf-8")
missing = []
for token in ("db:", "api:", "worker:", "caddy:"):
    if token not in text:
        missing.append(f"compose missing {token}")
if "127.0.0.1:8000" not in text:
    missing.append("api must bind loopback :8000 only")
if "healthcheck" not in text:
    missing.append("compose missing healthcheck blocks")
for token in ("handle /api/", "handle /mcp", "respond @internal 403", "handle /health"):
    if token not in caddy:
        missing.append(f"Caddyfile missing {token}")
if "koicloud.example" not in caddy:
    missing.append("Caddyfile must keep architecture domain placeholder")
header_match = re.search(r"(?ms)^[ \t]*header[ \t]*\{.*?^[ \t]*\}", caddy)
if header_match is None:
    missing.append(
        "Caddyfile must include a header block setting Strict-Transport-Security, "
        "X-Content-Type-Options nosniff, Referrer-Policy, and X-Frame-Options DENY"
    )
else:
    header_block = header_match.group(0)
    for header_name, header_value in SECURITY_HEADERS:
        if header_name not in header_block:
            missing.append(f"Caddyfile header block must set {header_name}")
        elif header_value is not None and header_value not in header_block:
            missing.append(
                f"Caddyfile header block must set {header_name} {header_value}"
            )
if ":80" not in caddy_http:
    missing.append("Caddyfile.http must bind :80")
if 'published: "8080"' not in http and "published: 8080" not in http and "8080:80" not in http:
    missing.append("http overlay must publish host port 8080")
for name in (
    "POSTGRES_PASSWORD",
    "JWT_SECRET",
    "NODE_TOKEN",
    "POND_PASSWORD_KEY",
    "MCP_DEMO_PASSWORD",
    "KOICLOUD_DOMAIN",
    "NODE_PUBLIC_HOST",
):
    if f"{name}=" not in env_names:
        missing.append(f".env.production.example missing {name}")
    # No values: line must be NAME= with nothing after (optional spaces).
for line in env_names.splitlines():
    if not line or line.lstrip().startswith("#"):
        continue
    if "=" not in line:
        missing.append(f"env line without =: {line}")
        continue
    key, _, val = line.partition("=")
    if val.strip():
        missing.append(f".env.production.example must have no values ({key})")
prod_src = Path("infra/docker-compose.prod.yml").read_text(encoding="utf-8")
if "EMAIL_PROVIDER:-console" in prod_src or "EMAIL_PROVIDER: ${EMAIL_PROVIDER:-console}" in prod_src:
    missing.append("prod compose must not default EMAIL_PROVIDER to console")
if "PAYMENT_PROVIDER:-simulated" in prod_src:
    missing.append("prod compose must not default PAYMENT_PROVIDER to simulated")
# Gate r7: ENVIRONMENT must be pinned so Settings console guard actually fires.
if "ENVIRONMENT: production" not in prod_src:
    missing.append("prod compose must pin ENVIRONMENT: production on services")
# Rendered config must carry ENVIRONMENT=production into the api container.
env_ok = any("ENVIRONMENT" in line and "production" in line for line in text.splitlines())
if not env_ok:
    missing.append("rendered prod compose must set ENVIRONMENT=production for api")
# With ENVIRONMENT=production, EMAIL_PROVIDER=console must not pass this check.
if any(
    line.strip() in {"EMAIL_PROVIDER: console", "EMAIL_PROVIDER:console"}
    or line.strip().startswith("EMAIL_PROVIDER:") and "console" in line
    for line in text.splitlines()
):
    missing.append(
        "EMAIL_PROVIDER=console is not allowed when ENVIRONMENT=production "
        "(startup would refuse; use a real provider in prod.env)"
    )
for service, key in REQUIRED_COMPOSE_ENV:
    block = service_block(prod_src, service)
    values = env_assignments(block).get(key, []) if block else []
    if len(values) != 1 or not uses_required_env(values[0], key):
        missing.append(
            f"{service} {key} must use required form ${{{key}:?...}} with no default"
        )
deploy_src = Path("infra/scripts/deploy.sh").read_text(encoding="utf-8")
if "need EMAIL_PROVIDER" not in deploy_src:
    missing.append("deploy.sh must need EMAIL_PROVIDER")
if "need PAYMENT_PROVIDER" not in deploy_src:
    missing.append("deploy.sh must need PAYMENT_PROVIDER")
if '== "console"' not in deploy_src:
    missing.append("deploy.sh must refuse EMAIL_PROVIDER=console before compose up")
if missing:
    raise SystemExit("\n".join(missing))
print("prod compose + Caddyfile + http overlay + names-only env OK")
PY
static_rc=$?
set -e

# Same keys as REQUIRED_COMPOSE_ENV. Omitted here so compose must fail closed.
cat >"$UNSET_ENV" <<'EOF'
POSTGRES_USER=koi
POSTGRES_DB=koicloud
REFRESH_TTL_DAYS=30
AGENT_MODE=docker
NODE_ID=node-prod
KOICLOUD_DOMAIN=koicloud.example
NODE_PUBLIC_HOST=db.gate-fixture.example
POND_PORT_RANGE_START=15000
POND_PORT_RANGE_END=15999
MCP_ENABLED=true
EMAIL_PROVIDER=resend
PAYMENT_PROVIDER=simulated
INVOICE_DIR=/var/lib/koicloud/invoices
BACKUP_DIR=/var/lib/koicloud/backups
INTERNAL_API_URL=http://127.0.0.1:8000/internal/v1
EOF
set +e
(
  unset POSTGRES_PASSWORD DATABASE_URL JWT_SECRET NODE_TOKEN POND_PASSWORD_KEY MCP_DEMO_PASSWORD
  $COMPOSE --env-file "$UNSET_ENV" \
    -f "$ROOT/infra/docker-compose.prod.yml" config \
    >/tmp/koicloud-prod-compose-unset.yml \
    2>/tmp/koicloud-prod-compose-unset.err
)
unset_rc=$?
set -e
unset_fail=0
if [[ "$unset_rc" -eq 0 ]]; then
  echo "expected docker compose config to fail when POSTGRES_PASSWORD, DATABASE_URL, JWT_SECRET, NODE_TOKEN, POND_PASSWORD_KEY, and MCP_DEMO_PASSWORD are unset" >&2
  if [[ -f /tmp/koicloud-prod-compose-unset.yml ]] && grep -q 'change-me' /tmp/koicloud-prod-compose-unset.yml; then
    keys="$(grep -E 'change-me' /tmp/koicloud-prod-compose-unset.yml | awk -F: '{gsub(/[[:space:]]/, "", $1); if ($1 != "") print $1}' | sort -u | tr '\n' ' ')"
    echo "rendered keys still using change-me defaults: ${keys}" >&2
  fi
  unset_fail=1
elif grep -Eq 'POSTGRES_PASSWORD|DATABASE_URL|JWT_SECRET|NODE_TOKEN|POND_PASSWORD_KEY|MCP_DEMO_PASSWORD' /tmp/koicloud-prod-compose-unset.err; then
  echo "prod compose config fails when required secrets are unset (exit ${unset_rc})"
else
  echo "docker compose config failed, but not because a required secret was unset" >&2
  cat /tmp/koicloud-prod-compose-unset.err >&2
  unset_fail=1
fi

# Negative: prod env with console must fail before serving traffic.
# Use non-placeholder host values so need() reaches the console guard.
cat >"$BAD_CONSOLE_ENV" <<'EOF'
POSTGRES_USER=koi
POSTGRES_PASSWORD=c0-console-reject-password-not-prod
POSTGRES_DB=koicloud
DATABASE_URL=postgresql+asyncpg://koi:c0-console-reject-password-not-prod@db:5432/koicloud
JWT_SECRET=c0-console-reject-jwt-secret-32bytes
REFRESH_TTL_DAYS=30
POND_PASSWORD_KEY=c0-console-reject-fernet-key-not-default==
AGENT_MODE=docker
NODE_ID=node-c0-console-reject
NODE_TOKEN=c0-console-reject-node-token
KOICLOUD_DOMAIN=localhost
NODE_PUBLIC_HOST=127.0.0.1
POND_PORT_RANGE_START=15000
POND_PORT_RANGE_END=15999
MCP_ENABLED=true
MCP_DEMO_PASSWORD=c0-console-reject-mcp-demo
EMAIL_PROVIDER=console
PAYMENT_PROVIDER=simulated
INVOICE_DIR=/var/lib/koicloud/invoices
BACKUP_DIR=/var/lib/koicloud/backups
INTERNAL_API_URL=http://127.0.0.1:8000/internal/v1
EOF
set +e
KOI_PROD_ENV="$BAD_CONSOLE_ENV" \
KOI_DEPLOY_CHECK_ONLY=1 \
KOI_DEPLOY_SKIP_GIT=1 \
KOI_DEPLOY_SKIP_WEB=1 \
KOI_DEPLOY_HTTP_PROXY=1 \
  bash "$ROOT/infra/scripts/deploy.sh" >/tmp/koicloud-console-deploy.out 2>/tmp/koicloud-console-deploy.err
console_rc=$?
set -e
if [[ "$console_rc" -eq 0 ]]; then
  echo "expected deploy.sh to refuse EMAIL_PROVIDER=console under prod; got exit 0" >&2
  cat /tmp/koicloud-console-deploy.out /tmp/koicloud-console-deploy.err >&2 || true
  exit 1
fi
if ! grep -q 'EMAIL_PROVIDER=console' /tmp/koicloud-console-deploy.err; then
  echo "deploy.sh refusal message missing EMAIL_PROVIDER=console" >&2
  cat /tmp/koicloud-console-deploy.err >&2 || true
  exit 1
fi
echo "deploy.sh correctly refuses EMAIL_PROVIDER=console before traffic (exit $console_rc)"
if [[ "$static_rc" -ne 0 || "$unset_fail" -ne 0 ]]; then
  exit 1
fi
