#!/usr/bin/env bash
# Apply Alembic migrations to the local control-plane DB.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/apps/api"

export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://koi:koi@127.0.0.1:5432/koicloud}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv no está en PATH. Instalá uv o corré migraciones dentro del contenedor api:" >&2
  echo "  docker compose exec api uv run alembic upgrade head" >&2
  exit 1
fi

uv run alembic upgrade head
echo "Migrations applied (alembic upgrade head)."
