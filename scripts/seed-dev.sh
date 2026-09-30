#!/usr/bin/env bash
# Seed the local control-plane DB with a verified demo user.
# Ensures migrations are applied first so `users` exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://koi:koi@127.0.0.1:5432/koicloud}"

bash "$ROOT/scripts/migrate-dev.sh"

cd "$ROOT/apps/api"

uv run python - <<'PY'
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user

ensure_demo_user()
print(f"Demo user ready: {DEMO_EMAIL} / {DEMO_PASSWORD} (email verified)")
PY
