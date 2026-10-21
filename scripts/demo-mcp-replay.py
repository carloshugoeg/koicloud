#!/usr/bin/env python3
"""Deterministic MCP demo fallback (W4-09 / E9-07).

Replays the sealed happy path without an LLM:

  create_pond(inventario-natural) -> confirm_action
  -> run_sql(SELECT now(), read) -> delete_pond -> confirm_action

Auth: HTTP Basic against POST /mcp (slug:password), same gate as Claude/Cursor.

Usage:
  python3 scripts/demo-mcp-replay.py --base-url http://127.0.0.1:8000 \\
      --slug demo-agent --password koicloud-demo --simulate-chat

  # second run is safe: deletes leftover inventario-natural first
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from typing import Any

POND_NAME = "inventario-natural"
SEQUENCE = (
    "create_pond",
    "confirm",
    "run_sql",
    "delete_pond",
    "confirm",
)


def _basic(slug: str, password: str) -> str:
    raw = f"{slug}:{password}".encode()
    return "Basic " + base64.b64encode(raw).decode()


class McpClient:
    def __init__(self, base_url: str, slug: str, password: str) -> None:
        self.url = base_url.rstrip("/") + "/mcp"
        self.auth = _basic(slug, password)
        self._id = 0

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": self.auth,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise SystemExit(f"HTTP {exc.code} from /mcp: {detail}") from exc
        if body.get("error"):
            raise SystemExit(f"JSON-RPC error: {body['error']}")
        result = body.get("result")
        if not isinstance(result, dict):
            raise SystemExit(f"unexpected result: {body!r}")
        return result


def _token(result: dict[str, Any]) -> str | None:
    for key in ("token", "confirmation_token"):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _say(simulate: bool, role: str, text: str) -> None:
    if simulate:
        print(f"{role}: {text}")
    else:
        print(text)


def _ensure_clean(client: McpClient, simulate: bool) -> None:
    """Idempotency: remove leftover inventario-natural from a prior run."""
    listed = client.call("list_ponds")
    ponds = listed.get("ponds") or listed.get("items") or []
    names = []
    if isinstance(ponds, list):
        for item in ponds:
            if isinstance(item, dict):
                names.append(item.get("name") or (item.get("pond") or {}).get("name"))
    if POND_NAME not in names:
        return
    _say(simulate, "system", f"limpiando residuo {POND_NAME} de una corrida anterior")
    proposed = client.call("delete_pond", {"name": POND_NAME})
    token = _token(proposed)
    if token:
        client.call("confirm_action", {"token": token})


def run(base_url: str, slug: str, password: str, simulate: bool) -> int:
    client = McpClient(base_url, slug, password)
    _ensure_clean(client, simulate)

    _say(simulate, "user", f"dame un pond nuevo llamado {POND_NAME}")
    created = client.call("create_pond", {"name": POND_NAME, "engine_version": "16"})
    summary = created.get("summary") or json.dumps(created, ensure_ascii=False)
    _say(simulate, "assistant", str(summary))
    token = _token(created)
    if not token:
        raise SystemExit(f"create_pond did not return a confirmation token: {created}")

    _say(simulate, "user", "confírmalo")
    confirmed = client.call("confirm_action", {"token": token})
    _say(simulate, "assistant", json.dumps(confirmed, ensure_ascii=False))

    _say(simulate, "user", f"corré SELECT now() contra {POND_NAME}")
    sql = client.call(
        "run_sql",
        {"pond_name": POND_NAME, "query": "SELECT now()", "mode": "read"},
    )
    _say(simulate, "assistant", json.dumps(sql, ensure_ascii=False))

    _say(simulate, "user", f"eliminá {POND_NAME} con backup previo")
    deleted = client.call("delete_pond", {"name": POND_NAME})
    summary = deleted.get("summary") or json.dumps(deleted, ensure_ascii=False)
    _say(simulate, "assistant", str(summary))
    token = _token(deleted)
    if not token:
        raise SystemExit(f"delete_pond did not return a confirmation token: {deleted}")

    _say(simulate, "user", "confírmalo")
    done = client.call("confirm_action", {"token": token})
    _say(simulate, "assistant", json.dumps(done, ensure_ascii=False))

    _say(simulate, "system", "replay OK · secuencia " + " -> ".join(SEQUENCE))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--slug", default="demo-agent")
    parser.add_argument("--password", default="koicloud-demo")
    parser.add_argument(
        "--simulate-chat",
        action="store_true",
        help="print a readable user/assistant transcript",
    )
    args = parser.parse_args(argv)
    return run(args.base_url, args.slug, args.password, args.simulate_chat)


if __name__ == "__main__":
    sys.exit(main())
