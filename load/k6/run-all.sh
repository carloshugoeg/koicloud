#!/usr/bin/env bash
# Run the three W4-08 scenarios and write JSON summaries under results/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
RESULTS="$ROOT/results"
mkdir -p "$RESULTS"
: "${BASE_URL:?Set BASE_URL to the API origin (no trailing slash)}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
commit="$(git -C "$ROOT/../.." rev-parse --short HEAD 2>/dev/null || echo unknown)"
outdir="$RESULTS/${stamp}-${commit}"
mkdir -p "$outdir"

for scenario in login list_ponds create_pond; do
  echo "==> k6 $scenario"
  k6 run \
    --summary-export "$outdir/${scenario}.summary.json" \
    --out json="$outdir/${scenario}.raw.json" \
    "$ROOT/scenarios/${scenario}.js" \
    | tee "$outdir/${scenario}.log"
done

echo "Wrote $outdir"
echo "Paste summaries into docs/reporte-carga.md (W4-12)."
