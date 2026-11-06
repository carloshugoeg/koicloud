"""Preview requirements must list every API runtime dep, including path packages."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _guards():
    path = REPO / "scripts" / "agent_guards.py"
    # run_path needs the module registered for dataclasses on 3.12.
    sys.modules.pop("agent_guards", None)
    return runpy.run_path(str(path), run_name="agent_guards")


def test_preview_requirements_include_koicloud_job_sanitize() -> None:
    guards = _guards()
    req = (REPO / "apps" / "web" / "requirements.txt").read_text(encoding="utf-8")
    names = guards["requirement_package_names"](req)
    assert "koicloud-job-sanitize" in names, (
        "apps/web/requirements.txt must list koicloud-job-sanitize. "
        "Run python apps/web/scripts/export-preview-requirements.py"
    )


def test_preview_requirements_pass_agent_guards_check() -> None:
    guards = _guards()
    findings = guards["check_preview_requirements"](REPO)
    assert findings == [], findings
