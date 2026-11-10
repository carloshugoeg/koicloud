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
PYPROJECT_OUT = WEB / "pyproject.toml"
VENDOR = WEB / "vendor"
SKIP = (
    re.compile(r"sys_platform\s*==\s*['\"]win32['\"]"),
    re.compile(r"sys_platform\s*==\s*['\"]emscripten['\"]"),
)
HEADER = (
    "# Generated from apps/api for Vercel Linux Python.\n"
    "# Win32/emscripten-only deps omitted (Vercel uv sync --locked).\n"
    "# Local path deps are vendored under apps/web/vendor (Vercel rejects ..).\n"
    "# Vercel prefers apps/web/pyproject.toml (native sources, no path rebase).\n"
    "# Regen: python apps/web/scripts/export-preview-requirements.py\n"
)
PYPROJECT_HEADER = (
    "# Generated from apps/api for Vercel Linux Python.\n"
    "# Native pyproject so Vercel skips requirements path rebasing onto the\n"
    "# repo root (which would make uv look under apps/web/apps/web/vendor).\n"
    "# Regen: python apps/web/scripts/export-preview-requirements.py\n"
)
REQ_PATH_DEP = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*@\s+(\S+)",
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
    """Map a local path dep to ``name @ vendor/<dir>`` (no filesystem writes)."""
    pkg_dir = _path_dep_dir(api, requirement)
    if pkg_dir is None:
        return requirement
    data = tomllib.loads((pkg_dir / "pyproject.toml").read_text(encoding="utf-8"))
    name = data.get("project", {}).get("name")
    if not name:
        return requirement
    # requirements.txt keeps a matchable name for guards. Install uses
    # apps/web/pyproject.toml tool.uv.sources (Vercel loads pyproject first).
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


def _exported_requirement_lines(api: Path) -> list[str]:
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
    return pkgs


def render_preview_requirements(api: Path) -> str:
    return HEADER + "\n".join(_exported_requirement_lines(api)) + "\n"


def render_preview_pyproject(api: Path) -> str:
    """Native pyproject.toml Vercel installs without rebasing path deps."""
    dependencies: list[str] = []
    sources: list[tuple[str, str]] = []
    for req in _exported_requirement_lines(api):
        match = REQ_PATH_DEP.match(req)
        if match is not None:
            name, path = match.group(1), match.group(2)
            dependencies.append(name)
            sources.append((name, path))
        else:
            dependencies.append(req)

    lines = [
        PYPROJECT_HEADER.rstrip("\n"),
        "[project]",
        'name = "koicloud-web-preview"',
        'version = "0.0.0"',
        'requires-python = "~=3.12.0"',
        "dependencies = [",
    ]
    for dep in dependencies:
        escaped = dep.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'  "{escaped}",')
    lines.extend(
        [
            "]",
            "",
            "[tool.uv]",
            "package = false",
            "",
        ]
    )
    if sources:
        lines.append("[tool.uv.sources]")
        for name, path in sources:
            lines.append(f'{name} = {{ path = "{path}" }}')
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    sync_vendor_path_deps(API)
    text = render_preview_requirements(API)
    OUT.write_text(text)
    pyproject = render_preview_pyproject(API)
    PYPROJECT_OUT.write_text(pyproject)
    pkgs = [line for line in text.splitlines() if line and not line.startswith("#")]
    print(f"wrote {len(pkgs)} requirements → {OUT}")
    print(f"wrote preview pyproject → {PYPROJECT_OUT}")


if __name__ == "__main__":
    main()
