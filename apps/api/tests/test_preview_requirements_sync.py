"""Preview requirements must list every API runtime dep, including path packages."""

from __future__ import annotations

import os
import re
import runpy
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WEB = REPO / "apps" / "web"
REQ_PATH_DEP = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*@\s+(\S+)",
)


def _guards():
    path = REPO / "scripts" / "agent_guards.py"
    # run_path needs the module registered for dataclasses on 3.12.
    sys.modules.pop("agent_guards", None)
    return runpy.run_path(str(path), run_name="agent_guards")


def _requirement_path_deps(text: str) -> list[tuple[str, str]]:
    deps: list[tuple[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        match = REQ_PATH_DEP.match(s.split(";", 1)[0].strip())
        if match is not None:
            deps.append((match.group(1), match.group(2)))
    return deps


def _vercel_rebase_path(path: str, *, working_dir: Path, package_root: Path) -> str:
    """Mirror @vercel/python-analysis rebasePath for requirements path deps.

    Vercel converts requirements.txt with workingDir=<rootDirectory> and
    packageRoot=<repo root>, then runs ``uv lock`` from rootDirectory.
    """
    if working_dir.resolve() == package_root.resolve():
        return path
    if Path(path).is_absolute():
        return path
    abs_path = (working_dir / path).resolve()
    rel = os.path.relpath(abs_path, package_root.resolve()).replace(os.sep, "/")
    if rel.startswith(".."):
        return rel
    return f"./{rel}"


def _uv_source_path(sources: object, name: str) -> str | None:
    if not isinstance(sources, dict):
        return None
    entry = sources.get(name)
    if entry is None:
        return None
    if isinstance(entry, list):
        if not entry:
            return None
        entry = entry[0]
    if isinstance(entry, dict):
        path = entry.get("path")
        return path if isinstance(path, str) else None
    return None


def test_preview_requirements_include_koicloud_job_sanitize() -> None:
    guards = _guards()
    req = (WEB / "requirements.txt").read_text(encoding="utf-8")
    names = guards["requirement_package_names"](req)
    assert "koicloud-job-sanitize" in names, (
        "apps/web/requirements.txt must list koicloud-job-sanitize. "
        "Run python apps/web/scripts/export-preview-requirements.py"
    )


def test_preview_requirements_pass_agent_guards_check() -> None:
    guards = _guards()
    findings = guards["check_preview_requirements"](REPO)
    assert findings == [], findings


def test_preview_path_deps_resolve_after_vercel_root_directory_rebase() -> None:
    """Vendored path deps must install when Vercel rootDirectory is apps/web.

    Vercel rebases relative requirements paths onto the repo root, then uv
    resolves them from apps/web (double-prefix). A native apps/web/pyproject.toml
    skips that rebase; otherwise the rebased path itself must exist.
    """
    req = (WEB / "requirements.txt").read_text(encoding="utf-8")
    path_deps = _requirement_path_deps(req)
    assert path_deps, "expected at least one path dep in apps/web/requirements.txt"

    pyproject_path = WEB / "pyproject.toml"
    if pyproject_path.is_file():
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        for name, _exported in path_deps:
            src_path = _uv_source_path(sources, name)
            assert src_path is not None, (
                f"apps/web/pyproject.toml must declare tool.uv.sources for {name}"
            )
            resolved = (WEB / src_path).resolve()
            assert (resolved / "pyproject.toml").is_file(), (
                f"{name}: pyproject source {src_path!r} resolves to {resolved} "
                "which has no pyproject.toml"
            )
        return

    for name, exported in path_deps:
        rebased = _vercel_rebase_path(
            exported, working_dir=WEB, package_root=REPO
        )
        resolved = (WEB / rebased).resolve()
        assert (resolved / "pyproject.toml").is_file(), (
            f"{name}: exported {exported!r} rebases to {rebased!r}; "
            f"uv from apps/web looks for {resolved} which is missing. "
            "Export a native apps/web/pyproject.toml with tool.uv.sources "
            "under vendor/, or place the package where the rebased path lands."
        )