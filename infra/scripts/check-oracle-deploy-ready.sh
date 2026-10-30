#!/usr/bin/env bash
# Asserts Oracle Always Free + sslip.io/nip.io deploy readiness (no live host).
# Fail-fast checks for Caddy hostname env, ARM-friendly bases, secret NAMES, ADR.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
from pathlib import Path

missing: list[str] = []

caddy = Path("infra/Caddyfile").read_text(encoding="utf-8")
if "{$KOICLOUD_DOMAIN" not in caddy:
    missing.append("Caddyfile must take hostname from {$KOICLOUD_DOMAIN}")
if "sslip.io" not in caddy and "nip.io" not in caddy:
    missing.append(
        "Caddyfile must document sslip.io/nip.io as valid KOICLOUD_DOMAIN values"
    )

compose = Path("infra/docker-compose.prod.yml").read_text(encoding="utf-8")
for image in ("postgres:16-alpine", "caddy:2.8-alpine"):
    if image not in compose:
        missing.append(f"prod compose missing multi-arch base {image}")
if "linux/amd64" in compose:
    missing.append("prod compose must not pin linux/amd64 (Oracle Ampere is arm64)")

for dockerfile in (
    Path("apps/api/Dockerfile"),
    Path("apps/node-agent/Dockerfile"),
):
    text = dockerfile.read_text(encoding="utf-8")
    if "FROM python:3.12-slim" not in text:
        missing.append(f"{dockerfile} must use python:3.12-slim (multi-arch)")
    if "linux/amd64" in text:
        missing.append(f"{dockerfile} must not pin linux/amd64")

overlay = Path("docker-compose.docker-agent.yml").read_text(encoding="utf-8")
if "AGENT_MODE: docker" not in overlay:
    missing.append("docker-compose.docker-agent.yml must set AGENT_MODE=docker")

env_names = Path("infra/.env.production.example").read_text(encoding="utf-8")
for name in (
    "JWT_SECRET",
    "POND_PASSWORD_KEY",
    "NODE_TOKEN",
    "MCP_DEMO_PASSWORD",
    "KOICLOUD_DOMAIN",
    "AGENT_MODE",
):
    if f"{name}=" not in env_names:
        missing.append(f".env.production.example missing {name}")

adr = Path("docs/adr/014-oracle-always-free-sslip.md")
if not adr.is_file():
    missing.append("missing ADR docs/adr/014-oracle-always-free-sslip.md")
else:
    body = adr.read_text(encoding="utf-8")
    for token in ("Oracle", "Always Free", "sslip.io", "Render", "Neon", "$0"):
        if token not in body:
            missing.append(f"ADR 014 must mention {token}")

deploy_doc = Path("docs/runbooks/deploy.md").read_text(encoding="utf-8")
for token in (
    "Oracle",
    "Always Free",
    "sslip.io",
    "15000-15999",
    "KOICLOUD_DEPLOY_HOST",
    "KOICLOUD_DEPLOY_SSH_KEY",
    "AGENT_MODE",
    "rollback",
):
    if token not in deploy_doc and token.lower() not in deploy_doc.lower():
        missing.append(f"docs/runbooks/deploy.md must cover {token}")

# Prove the Caddy site address is env-driven so <ip>.sslip.io works at apply time.
site_ok = any(
    line.strip().startswith("{$KOICLOUD_DOMAIN") and line.strip().endswith("{")
    for line in caddy.splitlines()
)
if not site_ok:
    missing.append("Caddyfile site block must be {$KOICLOUD_DOMAIN…} {")

if missing:
    raise SystemExit("\n".join(missing))
print("oracle deploy readiness OK (Caddy domain env, arm64 bases, ADR, runbook)")
PY
