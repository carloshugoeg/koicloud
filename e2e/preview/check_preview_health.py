#!/usr/bin/env python3
"""Assert preview /api/v1/health JSON matches the expected git sha (real apps/api)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_preview_health.py <sha> <health.json>", file=sys.stderr)
        return 2
    sha = sys.argv[1]
    path = Path(sys.argv[2])
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, TypeError):
        print("health not JSON", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or data.get("ok") is not True:
        print(f"health not ok: {raw[:200]}", file=sys.stderr)
        return 1
    # Legacy toy sim marked sim=true; real apps/api does not.
    if data.get("sim") is True:
        print(f"health still on e2e sim toy: {raw[:200]}", file=sys.stderr)
        return 1
    got = data.get("git_sha")
    if got != sha:
        print(f"sha mismatch got={got!r} want={sha!r}", file=sys.stderr)
        return 1
    print(raw[:240])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
