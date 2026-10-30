#!/usr/bin/env bash
set -uo pipefail
dir=$(cd "$(dirname "$0")" && pwd)
out=$("$dir/check.sh" ViolationProbe.tla ViolationProbe.cfg)
code=$?
printf '%s\n' "$out"
printf 'exit %s\n' "$code"
if [ "$code" -eq 1 ] && ! printf '%s\n' "$out" | grep -q '^PASS '; then
  echo "violation rejected"
  exit 0
fi
echo "expected exit 1 and no PASS line when an invariant is violated"
exit 1
