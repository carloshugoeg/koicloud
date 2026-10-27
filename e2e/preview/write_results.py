#!/usr/bin/env python3
"""Merge UI and MCP JSON rows into the preview verification table."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from redact import redact, secret_values  # noqa: E402  sibling module next to this script

PREVIEW = Path(__file__).resolve().parent
STORE_RESULTS = Path(
    "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/docs/e2e-verify-results.md"
)
STORE_CREDS = (
    "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/gate-access/credentials.json"
)

UI_FLOWS = (
    "auth login",
    "auth register",
    "auth error",
    "plans / simulated checkout",
    "pond create",
    "pond start (→ running)",
    "pond stop (sim)",
    "pond backup",
    "pond delete",
    "pond limits / errors",
    "SQL console",
    "admin suspend",
    "agent-access UI",
)

MCP_TOOLS = (
    "whoami",
    "list_ponds",
    "get_pond",
    "get_connection",
    "list_subscriptions",
    "list_backups",
    "create_pond",
    "delete_pond",
    "restore_backup",
    "run_sql",
    "confirm_action",
    "cancel_confirmation",
    "auth failure",
    "reconnect",
)

SLUGS = {
    "auth login": "auth-login",
    "auth register": "auth-register",
    "auth error": "auth-error",
    "plans / simulated checkout": "plans-checkout",
    "pond create": "pond-create",
    "pond start (→ running)": "pond-start",
    "pond stop (sim)": "pond-stop",
    "pond backup": "pond-backup",
    "pond delete": "pond-delete",
    "pond limits / errors": "pond-limits",
    "SQL console": "sql-console",
    "admin suspend": "admin-suspend",
    "agent-access UI": "agent-access",
}


def main() -> int:
    secrets = secret_values(os.environ.get("KOI_GATE_CREDENTIALS_OUT", STORE_CREDS))
    ui = _load(PREVIEW / "artifacts" / "ui-results.json")
    mcp = _load(Path(os.environ.get("KOI_MCP_RESULTS_OUT", str(PREVIEW / "artifacts" / "mcp-results.json"))))
    ui_by_flow = {_text(row.get("flow")): row for row in ui if isinstance(row, dict)}
    mcp_by_tool = {_text(row.get("tool")): row for row in mcp if isinstance(row, dict)}
    preview = os.environ.get(
        "PLAYWRIGHT_BASE_URL",
        "https://koicloud-web-git-w1-e2e-preview-verify-hugos-projects-3379fa36.vercel.app",
    )
    sha = (
        os.environ.get("KOI_GIT_SHA")
        or os.environ.get("GITHUB_SHA")
        or ""
    ).strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if run_id:
        run_cell = f"https://github.com/carloshugoeg/koicloud/actions/runs/{run_id}"
    else:
        run_cell = "local"
    lines = [
        "# E2E preview verification results",
        "",
        "Target: Vercel preview + simulated backend (test data only). Never production.",
        "Secrets: not listed here. Gate file path only (no values):",
        f"`{STORE_CREDS}`",
        "",
        f"Preview URL: {preview}",
        f"Head SHA: `{sha or 'unknown'}`",
        "",
        f"CI run (Playwright + MCP): {run_cell}",
        "",
        "PR: https://github.com/carloshugoeg/koicloud/pull/142 (draft, never merge)",
        "",
        "## Pond and product flows",
        "",
        "| Flow | Result | 375 | 1440 | Notes |",
        "|------|--------|-----|------|-------|",
    ]
    for flow in UI_FLOWS:
        row = ui_by_flow.get(flow, {})
        result = _result(row.get("result"))
        note = redact(_text(row.get("note")) or "not run", secrets)
        slug = SLUGS[flow]
        shot375 = "yes" if row.get("shot375") else "no"
        shot1440 = "yes" if row.get("shot1440") else "no"
        if flow == "pond stop (sim)" and result == "fail" and "404" in note:
            note = f"{note}. Preview has no stop control and the sim did not expose one."
        lines.append(f"| {flow} | {result} | {shot375} | {shot1440} | {note} |")
    lines.extend(
        [
            "",
            "## MCP tools (real JSON-RPC client → preview `/mcp`, proxied to sim)",
            "",
            "| Tool | Result | Notes |",
            "|------|--------|-------|",
        ]
    )
    for tool in MCP_TOOLS:
        row = mcp_by_tool.get(tool, {})
        result = _result(row.get("result"))
        note = redact(_text(row.get("note")) or "not run", secrets)
        lines.append(f"| {tool} | {result} | {note} |")
    lines.extend(
        [
            "",
            "## Follow-up fix PRs",
            "",
            "| Failure | Fix PR |",
            "|---------|--------|",
            "| _(none yet)_ | |",
            "",
        ]
    )
    text = "\n".join(lines)
    target = Path(os.environ.get("KOI_E2E_RESULTS_OUT", str(STORE_RESULTS)))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target}", flush=True)
    return 0


def _load(path: Path) -> list[object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return payload
    return []


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.replace("|", "/")
    return ""


def _result(value: object) -> str:
    if value in {"pass", "fail"}:
        return str(value)
    return "fail"


if __name__ == "__main__":
    raise SystemExit(main())
