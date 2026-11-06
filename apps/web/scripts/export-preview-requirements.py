#!/usr/bin/env python3
"""Export apps/api deps for Vercel Linux Python (omit win32/emscripten-only)."""
from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
API = WEB.parent / "api"
OUT = WEB / "requirements.txt"
VENDOR = WEB / "vendor"
SKIP = (
    re.compile(r"sys_platform\s*==\s*['\"]win32['\"]"),
    re.compile(r"sys_platform\s*==\s*['\"]emscripten['\"]"),
)
HEADER = (
    "# Generated from apps/api for Vercel Linux Python.\n"
    "# Win32/emscripten-only deps omitted (Vercel uv sync --locked).\n"
    "# Local path deps are vendored under apps/web/vendor (Vercel rejects ..).\n"
    "# Regen: python apps/web/scripts/export-preview-requirements.py\n"
)


def _path_dep_dir(api: Path, requirement: str) -> Path | None:
    if " @" in requirement or requirement.startswith("-e "):
        return None
    if not (requirement.startswith(".") or requirement.startswith("..")):
        return None
    pkg_dir = (api / requirement).resolve()
    if not (pkg_dir / "pyproject.toml").is_file():
        return None
    return pkg_dir


def _named_vendored_requirement(api: Path, requirement: str) -> str:
    """Map a local path dep to ``name @ ./vendor/<dir>`` (no filesystem writes)."""
    pkg_dir = _path_dep_dir(api, requirement)
    if pkg_dir is None:
        return requirement
    data = tomllib.loads((pkg_dir / "pyproject.toml").read_text(encoding="utf-8"))
    name = data.get("project", {}).get("name")
    if not name:
        return requirement
    # No leading "./": Vercel rewrites "./vendor/..." to "apps/web/vendor/..." and
    # then resolves that again from apps/web, producing apps/web/apps/web/vendor.
    return f"{name} @ vendor/{pkg_dir.name}"


def sync_vendor_path_deps(api: Path) -> None:
    """Copy local path deps into apps/web/vendor for Vercel install."""
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
    VENDOR.mkdir(parents=True, exist_ok=True)
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if any(p.search(s) for p in SKIP):
            continue
        req = s.split(";", 1)[0].strip()
        pkg_dir = _path_dep_dir(api, req)
        if pkg_dir is None:
            continue
        dest = VENDOR / pkg_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(
            pkg_dir,
            dest,
            ignore=shutil.ignore_patterns(
                ".venv", "__pycache__", "*.pyc", "*.egg-info"
            ),
        )


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
        pkgs.append(_named_vendored_requirement(api, req))
    return HEADER + "\n".join(pkgs) + "\n"


def main() -> None:
    sync_vendor_path_deps(API)
    text = render_preview_requirements(API)
    OUT.write_text(text)
    pkgs = [line for line in text.splitlines() if line and not line.startswith("#")]
    print(f"wrote {len(pkgs)} requirements → {OUT}")


if __name__ == "__main__":
    main()
