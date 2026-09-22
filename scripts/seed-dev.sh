#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Phase 0 scaffold only.

This repo already seeds the plans through alembic 0002_seed_plans.
A full demo seed script will create the demo user, subscription and mock pond in a later slice.
EOF
