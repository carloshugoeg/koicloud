#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
RESULTS="$ROOT/results"

if [ -z "${BASE_URL:-}" ]; then
  echo "BASE_URL is required. Example: http://127.0.0.1:8000" >&2
  exit 2
fi

mkdir -p "$RESULTS"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
commit="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"
outdir="$RESULTS/${stamp}-${commit}"
mkdir -p "$outdir"
if ! git -C "$REPO" rev-parse HEAD >"$outdir/commit.txt" 2>/dev/null; then
  echo "unknown" >"$outdir/commit.txt"
fi

fail=0
for scenario in login list_ponds create_pond; do
  echo "==> k6 ${scenario}"
  if ! k6 run --summary-export "$outdir/${scenario}.summary.json" "$ROOT/scenarios/${scenario}.js"; then
    echo "threshold or runtime failure: ${scenario}" >&2
    fail=1
  fi
done

echo "Wrote ${outdir}"
exit "$fail"
