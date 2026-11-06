#!/usr/bin/env python3
"""Export apps/api deps for Vercel Linux Python (omit win32/emscripten-only)."""
from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
API = WEB.parent / "api"
OUT = WEB / "requirements.txt"
SKIP = (
    re.compile(r"sys_platform\s*==\s*['\"]win32['\"]"),
    re.compile(r"sys_platform\s*==\s*['\"]emscripten['\"]"),
)
HEADER = (
    "# Generated from apps/api for Vercel Python on Linux.\n"
    "# Win32/emscripten-only deps omitted (Vercel uv sync --locked).\n"
    "# Regen: python apps/web/scripts/export-preview-requirements.py\n"
)


def _named_path_requirement(api: Path, requirement: str) -> str:
    """Turn a bare local path into ``name @ path`` so guards can see the package name."""
    if " @" in requirement or requirement.startswith("-e "):
        return requirement
    candidate = Path(requirement)
    if candidate.is_absolute() or not (
        requirement.startswith(".") or requirement.startswith("..")
    ):
        return requirement
    pkg_dir = (api / requirement).resolve()
    pyproject = pkg_dir / "pyproject.toml"
    if not pyproject.is_file():
        return requirement
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    name = data.get("project", {}).get("name")
    if not name:
        return requirement
    return f"{name} @ {requirement}"


def render_preview_requirements(api: Path) -> str:
    raw = subprocess.check_output(
        [
            "uv",
            "export",
            "--no-dev",
            "--no-hashes",
            "--no-emit-project",
            "--format",
            "requirements.txt",
        ],
        cwd=api,
        text=True,
    )
    pkgs: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if any(p.search(s) for p in SKIP):
            continue
        req = s.split(";", 1)[0].strip()
        pkgs.append(_named_path_requirement(api, req))
    return HEADER + "\n".join(pkgs) + "\n"


def main() -> None:
    text = render_preview_requirements(API)
    OUT.write_text(text)
    pkgs = [line for line in text.splitlines() if line and not line.startswith("#")]
    print(f"wrote {len(pkgs)} requirements → {OUT}")


if __name__ == "__main__":
    main()
