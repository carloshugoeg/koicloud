#!/usr/bin/env bash
# Seed the local control-plane DB with a verified demo user.
# Requires Postgres reachable (compose `db` up) and migrations applied.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/apps/api"

# Host-side default. Inside Compose, DATABASE_URL already points at `db`.
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://koi:koi@127.0.0.1:5432/koicloud}"

uv run python - <<'PY'
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user

ensure_demo_user()
print(f"Demo user ready: {DEMO_EMAIL} / {DEMO_PASSWORD} (email verified)")
PY
