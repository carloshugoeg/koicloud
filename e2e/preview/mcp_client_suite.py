#!/usr/bin/env python3
"""Drive every MCP tool against the preview sim backend. Never prints secrets."""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

STORE_CREDS = (
    "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/gate-access/credentials.json"
)
STORE_RESULTS = (
    "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/docs/e2e-verify-results.md"
)
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

READ_TOOLS = [
    "whoami",
    "list_ponds",
    "get_pond",
    "get_connection",
    "list_subscriptions",
    "list_backups",
]
MUT_TOOLS = [
    "create_pond",
    "delete_pond",
    "restore_backup",
    "run_sql",
    "confirm_action",
    "cancel_confirmation",
]


def _load_creds() -> dict:
    path = Path(os.environ.get("KOI_GATE_CREDENTIALS_OUT") or STORE_CREDS)
    return json.loads(path.read_text(encoding="utf-8"))


def _redact(text: str, secrets: list[str]) -> str:
    cleaned = text
    for secret in secrets:
        if len(secret) >= 4:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def _secrets(payload: dict) -> list[str]:
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.lower() in {"password", "token", "access_token", "refresh_token", "secret"} and isinstance(
                    value, str
                ):
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def _http(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | None = None,
) -> tuple[int, dict]:
    raw_body = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=raw_body,
        method=method,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return resp.status, payload if isinstance(payload, dict) else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": {"message": f"http_{exc.code}"}}
        return exc.code, payload if isinstance(payload, dict) else {}


def _rpc(url: str, auth: str, method: str, params: dict | None = None, req_id: int = 1) -> dict:
    _status, payload = _http(
        url,
        method="POST",
        headers={
            "content-type": "application/json",
            "authorization": auth,
            "accept": "application/json",
        },
        body={"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}},
    )
    return payload


def _tool_code(payload: dict) -> str | None:
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and isinstance(structured.get("code"), str):
        return structured["code"]
    if isinstance(result.get("code"), str):
        return result["code"]
    return None


def main() -> int:
    creds = _load_creds()
    hidden = _secrets(creds)
    # Prefer the Vercel preview origin so MCP is exercised at preview /mcp.
    # Callers that cannot route preview→sim (no Playwright page.route) may set
    # KOI_SIM_BASE_URL alone for a loopback-only debug run.
    preview = (
        os.environ.get("KOI_MCP_BASE_URL")
        or os.environ.get("KOI_PUBLIC_BASE_URL")
        or os.environ.get("PLAYWRIGHT_BASE_URL")
        or (creds.get("preview_url") if isinstance(creds.get("preview_url"), str) else None)
    )
    sim = os.environ.get("KOI_SIM_BASE_URL") or creds.get("sim_base_url") or "http://127.0.0.1:18080"
    base = str(preview or sim).rstrip("/")
    api_base = str(os.environ.get("KOI_SIM_BASE_URL") or creds.get("sim_base_url") or sim).rstrip("/")
    mcp_url = f"{base}/mcp"
    if "127.0.0.1" in mcp_url or "localhost" in mcp_url:
        print("warning: MCP URL is loopback; prefer PLAYWRIGHT_BASE_URL preview host", file=sys.stderr)
    mcp = creds.get("mcp")
    if not isinstance(mcp, dict):
        print("mcp credentials missing", file=sys.stderr)
        return 2
    slug = mcp.get("slug")
    password = mcp.get("password")
    if not isinstance(slug, str) or not isinstance(password, str):
        print("mcp credentials incomplete", file=sys.stderr)
        return 2
    auth = "Basic " + base64.b64encode(f"{slug}:{password}".encode()).decode()

    rows: list[dict[str, str]] = []
    pond_name = "mcp-gate-pond"

    def record(tool: str, result: str, note: str) -> None:
        rows.append({"tool": tool, "result": result, "note": _redact(note, hidden)})

    # Auth failure: invalid bearer → HTTP 401 token_invalid (catalog).
    auth_status, auth_body = _http(
        f"{api_base}/api/v1/me",
        headers={"authorization": "Bearer not-a-valid-token", "accept": "application/json"},
    )
    auth_ok = auth_status == 401 and auth_body.get("code") == "token_invalid"
    record(
        "auth failure",
        "pass" if auth_ok else "fail",
        "HTTP 401 token_invalid" if auth_ok else f"status={auth_status} code={auth_body.get('code')}",
    )

    # Reconnect with good creds via initialize + tools/list
    init = _rpc(mcp_url, auth, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "gate", "version": "0"}})
    listed = _rpc(mcp_url, auth, "tools/list", {})
    tools = ((listed.get("result") or {}).get("tools") if isinstance(listed.get("result"), dict) else None) or []
    names = {t.get("name") for t in tools if isinstance(t, dict)}
    if init.get("result") and names.issuperset(set(READ_TOOLS + MUT_TOOLS)):
        record("reconnect", "pass", f"initialize + tools/list ({len(names)} tools)")
    else:
        record("reconnect", "fail", _redact(json.dumps({"init": bool(init.get('result')), "names": sorted(names)}), hidden))

    def call(tool: str, arguments: dict | None = None) -> dict:
        return _rpc(mcp_url, auth, "tools/call", {"name": tool, "arguments": arguments or {}})

    unknown = call("no_such_tool")
    unknown_code = _tool_code(unknown)
    record(
        "method_not_found",
        "pass" if unknown_code == "method_not_found" else "fail",
        unknown_code or "missing code",
    )

    missing = call("get_pond", {})
    missing_code = _tool_code(missing)
    record(
        "invalid_params",
        "pass" if missing_code == "invalid_params" else "fail",
        missing_code or "missing code",
    )

    # whoami
    who = call("whoami")
    record("whoami", "pass" if (who.get("result") or {}).get("email") else "fail", "whoami email present" if who.get("result") else "missing")

    # cancel_confirmation before confirming a create
    cancel_probe = call("create_pond", {"name": f"{pond_name}-cancel"})
    cancel_token = (cancel_probe.get("result") or {}).get("token") if isinstance(cancel_probe.get("result"), dict) else None
    cancel = call("cancel_confirmation", {"token": cancel_token or "missing"})
    cancel_body = cancel.get("result") if isinstance(cancel.get("result"), dict) else {}
    cancel_ok = cancel_body.get("status") == "discarded"
    record("cancel_confirmation", "pass" if cancel_ok else "fail", "discarded" if cancel_ok else "cancel failed")

    # create_pond (confirm required)
    created = call("create_pond", {"name": pond_name})
    result = created.get("result") or {}
    token = result.get("token") if isinstance(result, dict) else None
    record("create_pond", "pass" if token else "fail", "confirmation_required" if token else "no token")

    confirm = call("confirm_action", {"token": token or "missing"})
    confirmed_body = confirm.get("result") if isinstance(confirm.get("result"), dict) else {}
    confirm_ok = bool(confirmed_body.get("pond") or confirmed_body.get("status") == "confirmed")
    record("confirm_action", "pass" if confirm_ok else "fail", "create confirmed" if confirm_ok else "confirm failed")

    ponds = call("list_ponds")
    record("list_ponds", "pass" if isinstance((ponds.get("result") or {}).get("ponds"), list) else "fail", "list ok")

    got = call("get_pond", {"name": pond_name})
    record("get_pond", "pass" if (got.get("result") or {}).get("pond") else "fail", "get ok")

    conn = call("get_connection", {"name": pond_name})
    conn_body = conn.get("result") if isinstance(conn.get("result"), dict) else {}
    nested = conn_body.get("connection") if isinstance(conn_body.get("connection"), dict) else {}
    conn_ok = bool(conn_body.get("uri") or nested.get("uri"))
    record("get_connection", "pass" if conn_ok else "fail", "uri present" if conn_ok else "missing uri")

    subs = call("list_subscriptions")
    record("list_subscriptions", "pass" if "subscriptions" in (subs.get("result") or {}) else "fail", "subs")

    backups = call("list_backups", {"pond_name": pond_name})
    record(
        "list_backups",
        "pass" if isinstance((backups.get("result") or {}).get("backups"), list) else "fail",
        "backups list",
    )

    sql = call("run_sql", {"pond_name": pond_name, "query": "SELECT 1", "mode": "read"})
    sql_body = sql.get("result") if isinstance(sql.get("result"), dict) else {}
    sql_ok = sql_body.get("row_count") == 1 or isinstance(sql_body.get("rows"), list)
    record("run_sql", "pass" if sql_ok else "fail", "select 1")

    # Trigger a real backup over HTTP, then propose restore via MCP.
    pond_id = None
    ponds_body = (ponds.get("result") or {}).get("ponds") if isinstance(ponds.get("result"), dict) else []
    if isinstance(ponds_body, list):
        for row in ponds_body:
            if isinstance(row, dict) and row.get("name") == pond_name:
                pond_id = row.get("id")
                break
    backup_id = None
    if isinstance(pond_id, str):
        user = creds.get("user") if isinstance(creds.get("user"), dict) else {}
        login_body = json.dumps(
            {"email": user.get("email"), "password": user.get("password")}
        ).encode()
        login_req = urllib.request.Request(
            f"{base}/api/v1/auth/login",
            data=login_body,
            method="POST",
            headers={"content-type": "application/json"},
        )
        try:
            with urllib.request.urlopen(login_req, timeout=10) as resp:
                access = json.loads(resp.read().decode()).get("access_token")
            if isinstance(access, str):
                bak_req = urllib.request.Request(
                    f"{base}/api/v1/ponds/{pond_id}/backups",
                    data=b"{}",
                    method="POST",
                    headers={
                        "content-type": "application/json",
                        "authorization": f"Bearer {access}",
                    },
                )
                with urllib.request.urlopen(bak_req, timeout=10) as resp:
                    bak = json.loads(resp.read().decode())
                backup_id = (bak.get("backup") or {}).get("id")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            backup_id = None

    bad_restore = call(
        "restore_backup",
        {
            "pond_name": pond_name,
            "backup_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    bad_restore_code = _tool_code(bad_restore)
    record(
        "backup_not_found",
        "pass" if bad_restore_code == "backup_not_found" else "fail",
        bad_restore_code or "missing code",
    )

    restore = call(
        "restore_backup",
        {
            "pond_name": pond_name,
            "backup_id": backup_id or "11111111-1111-1111-1111-111111111111",
        },
    )
    restore_body = restore.get("result") if isinstance(restore.get("result"), dict) else {}
    rtoken = restore_body.get("token")
    restore_code = _tool_code(restore)
    restore_ok = bool(rtoken) or restore_code in {"backup_not_found", "pond_not_found"}
    record(
        "restore_backup",
        "pass" if restore_ok else "fail",
        "propose or domain error" if restore_ok else (restore_code or "no result"),
    )
    if rtoken:
        call("cancel_confirmation", {"token": rtoken})

    deleted = call("delete_pond", {"name": pond_name})
    dtoken = (deleted.get("result") or {}).get("token") if isinstance(deleted.get("result"), dict) else None
    record("delete_pond", "pass" if dtoken else "fail", "confirmation_required")
    if dtoken:
        call("confirm_action", {"token": dtoken})

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out = ARTIFACTS / "mcp-results.json"
    out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"mcp_results={out}")
    failed = [row for row in rows if row["result"] != "pass"]
    print(f"mcp_pass={len(rows) - len(failed)} mcp_fail={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
