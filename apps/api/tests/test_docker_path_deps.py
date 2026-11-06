"""Path deps must stay installable inside each image build context."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

# Compose files that build the API / node-agent images in CI and prod.
COMPOSE_BUILDS = (
    ("e2e/docker-compose.yml", "api"),
    ("e2e/docker-compose.yml", "worker"),
    ("e2e/docker-compose.yml", "node-agent"),
    ("infra/docker-compose.prod.yml", "api"),
    ("infra/docker-compose.prod.yml", "worker"),
)

PATH_DEP_RE = re.compile(
    r'^([A-Za-z0-9][A-Za-z0-9._-]*)\s*=\s*\{\s*path\s*=\s*"([^"]+)"',
    re.MULTILINE,
)
INSTRUCTION_RE = re.compile(r"^(COPY|WORKDIR)\s+(.+)$")


def _service_build(compose_text: str, service: str) -> tuple[str, str | None]:
    """Return (context, dockerfile_or_None) for a compose service build."""
    lines = compose_text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line == f"  {service}:":
            start = index + 1
            break
    if start is None:
        raise AssertionError(f"service {service} missing from compose")
    context: str | None = None
    dockerfile: str | None = None
    in_build = False
    for line in lines[start:]:
        if line.startswith("  ") and not line.startswith("   ") and line.strip():
            break
        stripped = line.strip()
        if stripped.startswith("build:"):
            rest = stripped[len("build:") :].strip()
            if rest and not rest.startswith("{") and not rest.startswith("|"):
                context = rest
                break
            in_build = True
            continue
        if not in_build:
            continue
        if line.startswith("    ") and not line.startswith("     ") and stripped and ":" in stripped:
            if not stripped.startswith("context:") and not stripped.startswith("dockerfile:"):
                break
        if stripped.startswith("context:"):
            context = stripped.split(":", 1)[1].strip().strip("\"'")
        elif stripped.startswith("dockerfile:"):
            dockerfile = stripped.split(":", 1)[1].strip().strip("\"'")
    if context is None:
        raise AssertionError(f"{service} build context missing")
    return context, dockerfile


def _path_deps(pyproject: Path) -> list[tuple[str, Path]]:
    text = pyproject.read_text(encoding="utf-8")
    deps: list[tuple[str, Path]] = []
    for match in PATH_DEP_RE.finditer(text):
        name, rel = match.group(1), match.group(2)
        deps.append((name, (pyproject.parent / rel).resolve()))
    return deps


def _compose_context_dir(compose_file: Path, context: str) -> Path:
    return (compose_file.parent / context).resolve()


def _dockerfile_for(compose_file: Path, context: str, dockerfile: str | None) -> Path:
    context_dir = _compose_context_dir(compose_file, context)
    if dockerfile:
        # Compose resolves a relative dockerfile path from the build context.
        return (context_dir / dockerfile).resolve()
    return (context_dir / "Dockerfile").resolve()


def _host_path(dest: Path, absolute: Path) -> Path:
    if absolute.as_posix() in {"", "/"}:
        return dest
    return dest / absolute.as_posix().lstrip("/")


def _materialize_image_tree(dockerfile: Path, context: Path, dest: Path) -> Path:
    """Apply WORKDIR/COPY from the Dockerfile against context into dest. Return WORKDIR."""
    workdir = Path("/")
    for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = INSTRUCTION_RE.match(line)
        if match is None:
            continue
        kind, rest = match.group(1), match.group(2).strip()
        if kind == "WORKDIR":
            raw = rest.split()[0]
            workdir = Path(raw) if raw.startswith("/") else workdir / raw
            continue
        parts = rest.split()
        if not parts or parts[0].startswith("--"):
            continue
        if len(parts) < 2:
            raise AssertionError(f"{dockerfile}: unsupported COPY: {line}")
        sources = parts[:-1]
        dst = parts[-1]
        if dst.startswith("/"):
            dest_base = Path(dst)
        else:
            dest_base = workdir / dst

        # Docker: multiple sources, trailing slash, or "." means copy into a directory.
        into_dir = len(sources) > 1 or dst.endswith("/") or dst in {".", "./"}
        for src in sources:
            src_path = context / src
            if into_dir:
                dest_path = _host_path(dest, dest_base) / Path(src).name
            else:
                dest_path = _host_path(dest, dest_base)
            if src_path.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(
                    src_path,
                    dest_path,
                    ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc"),
                )
            elif src_path.is_file():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
            else:
                raise AssertionError(
                    f"{dockerfile}: COPY source missing in context: {src}"
                )
    return workdir


@pytest.mark.parametrize("compose_rel,service", COMPOSE_BUILDS)
def test_compose_build_context_covers_path_deps(compose_rel: str, service: str) -> None:
    compose_file = REPO / compose_rel
    text = compose_file.read_text(encoding="utf-8")
    context_rel, _dockerfile = _service_build(text, service)
    context = _compose_context_dir(compose_file, context_rel)

    if service == "node-agent":
        pyproject = REPO / "apps" / "node-agent" / "pyproject.toml"
    else:
        pyproject = REPO / "apps" / "api" / "pyproject.toml"

    missing = [
        f"{name} -> {path}"
        for name, path in _path_deps(pyproject)
        if not path.is_relative_to(context)
    ]
    assert not missing, (
        f"{compose_rel} service {service}: build context {context} does not contain "
        f"path dependencies {missing}. Image uv sync cannot see them."
    )


@pytest.mark.parametrize(
    "app_dir,compose_rel,service",
    [
        ("apps/api", "e2e/docker-compose.yml", "api"),
        ("apps/node-agent", "e2e/docker-compose.yml", "node-agent"),
    ],
)
def test_image_tree_uv_sync_frozen_with_path_deps(
    app_dir: str, compose_rel: str, service: str
) -> None:
    """Materialize what the Dockerfile copies, then freeze-sync like CI."""
    if shutil.which("uv") is None:
        pytest.skip("uv is required")

    compose_file = REPO / compose_rel
    context_rel, dockerfile_rel = _service_build(
        compose_file.read_text(encoding="utf-8"), service
    )
    context = _compose_context_dir(compose_file, context_rel)
    dockerfile = _dockerfile_for(compose_file, context_rel, dockerfile_rel)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workdir = _materialize_image_tree(dockerfile, context, root)
        project = root / workdir.as_posix().lstrip("/")
        assert (project / "pyproject.toml").is_file(), project
        assert (project / "uv.lock").is_file(), project
        env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
        result = subprocess.run(
            ["uv", "sync", "--frozen"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert result.returncode == 0, (
            f"{app_dir} image tree uv sync --frozen failed under {project} "
            f"(context={context}):\n{result.stderr or result.stdout}"
        )


def test_api_and_node_agent_declare_job_sanitize_path_dep() -> None:
    """Sanity: both images depend on the shared package this suite guards."""
    for rel in ("apps/api/pyproject.toml", "apps/node-agent/pyproject.toml"):
        data = tomllib.loads((REPO / rel).read_text(encoding="utf-8"))
        deps = data.get("project", {}).get("dependencies", [])
        assert any("koicloud-job-sanitize" in str(item) for item in deps), rel
        sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        assert "koicloud-job-sanitize" in sources, rel
