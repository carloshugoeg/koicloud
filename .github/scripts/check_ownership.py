#!/usr/bin/env python3
"""Fail if a PR branch changes files outside its workstream's owned paths.

Usage (CI):  python .github/scripts/check_ownership.py --branch "$HEAD_REF" --base "origin/$BASE_REF" [--labels "a,b"]

The owned paths mirror docs/WORKSTREAMS.md and docs/architecture/agent-docs.md.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys

OWNED: dict[str, list[str]] = {
    "w1": [
        "apps/api/app/core/**",
        "apps/api/app/commands/**",
        "apps/api/app/internal_api/**",
        "apps/api/app/workers/**",
        "apps/api/app/tooling/**",
        "apps/api/app/main.py",
        "apps/api/app/api_v1.py",
        "apps/api/app/internal_v1.py",
        "apps/api/app/schemas.py",
        "apps/api/app/modules/ponds/**",
        "apps/api/app/modules/jobs/**",
        "apps/api/app/modules/nodes/**",
        "apps/api/app/modules/backups/**",
        "apps/api/app/modules/metering/**",
        "apps/api/app/modules/agent_access/**",
        "apps/api/alembic/**",
        "apps/api/alembic.ini",
        "apps/api/pyproject.toml",
        "apps/api/uv.lock",
        "apps/node-agent/**",
        "packages/contracts/**",
        "docker-compose.yml",
        "Makefile",
        ".env.example",
        ".gitignore",
        "README.md",
        "LICENSE",
        ".github/**",
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".cursor/**",
        ".agents/**",
        "docs/architecture/**",
        "docs/branch-naming.md",
        "docs/agent-onboarding.md",
        "docs/WORKSTREAMS.md",
        "docs/visual-guidelines.md",
        "docs/visual-guidelines-agent-prompt.md",
        "docs/tickets/**",
        "docs/runbooks/**",
        "scripts/**",
    ],
    "w2": ["apps/web/**"],
    "w3": [
        "apps/api/app/modules/auth/**",
        "apps/api/app/modules/users/**",
        "apps/api/app/modules/billing/**",
        "apps/api/app/modules/notifications/**",
        "apps/api/app/modules/admin/**",
    ],
    "w4": [
        "apps/api/app/modules/sql_console/**",
        "apps/api/app/mcp/**",
        "apps/cli/**",
        "infra/**",
        "load/**",
        ".github/workflows/deploy.yml",
        "docs/manual-tecnico.md",
        "docs/manual-usuario.md",
        "docs/manual-usuario/**",
        "docs/reporte-carga.md",
    ],
}

# Dependency manifests (package.json, pnpm-lock.yaml, apps/cli/pyproject.toml, uv.lock) and
# .github/workflows/deploy.yml are editable by their workstream; CODEOWNERS additionally requires
# W1 approval for them. Nothing to enforce here.


def matches(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat.endswith("/**"):
            if path.startswith(pat[:-3] + "/") or path == pat[:-3]:
                return True
        elif fnmatch.fnmatch(path, pat):
            return True
    return False


def changed_files(base: str) -> list[str]:
    out = subprocess.check_output(["git", "diff", "--name-only", f"{base}...HEAD"], text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def branch_prefix(branch_name: str) -> str | None:
    match = re.match(r"^(w[1-4])(?:[-/].+)?$", branch_name.lower())
    if match:
        return match.group(1)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--labels", default="")
    args = ap.parse_args()

    labels = {label.strip() for label in args.labels.split(",") if label.strip()}
    prefix = branch_prefix(args.branch)
    if prefix is None or prefix not in OWNED:
        print(f"::error::Branch '{args.branch}' must start with w1-, w2-, w3- or w4-.")
        return 1

    files = changed_files(args.base)

    if prefix == "w1":
        # W1 owns everything by default (AGENTS.md §3). Only warn when it enters another workstream's paths.
        foreign = [p for p in files if any(matches(p, OWNED[w]) for w in ("w2", "w3", "w4")) and not matches(p, OWNED["w1"])]
        for path in foreign:
            print(f"::warning::w1 branch touches {path} (owned by another workstream); mention it in the PR")
        print(f"ownership OK (w1): {len(files)} file(s), {len(foreign)} in other workstreams' paths")
        return 0

    allowed = OWNED[prefix]
    violations = [path for path in files if not matches(path, allowed)]

    if violations and "cross-workstream" in labels:
        print("::notice::cross-workstream label present; CODEOWNERS will require the owners' approval for:")
        for path in violations:
            print(f"  - {path}")
        return 0

    if violations:
        print(f"::error::Branch '{args.branch}' ({prefix.upper()}) changes files outside its owned paths:")
        for path in violations:
            print(f"  - {path}")
        print("Open a ticket for the owning workstream or a CCR (docs/architecture/agent-docs.md). "
              "If this is an approved cross-workstream change, add the 'cross-workstream' label.")
        return 1

    print(f"ownership OK: {len(files)} file(s) within {prefix.upper()} paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
