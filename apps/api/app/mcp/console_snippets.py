"""Config snippets for console MCP clients using pond temporary access.

One registry drives Claude Code, Cursor CLI, and Codex CLI. Docs and smoke
tests share this module so the pasted credential stays the same shape as the
HTTP headers the gate accepts.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Literal

ConsoleClientId = Literal["claude_code", "cursor_cli", "codex_cli"]

CONSOLE_CLIENTS: tuple[ConsoleClientId, ...] = (
    "claude_code",
    "cursor_cli",
    "codex_cli",
)


def basic_authorization(slug: str, password: str) -> str:
    token = base64.b64encode(f"{slug}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def build_snippet(
    client_id: ConsoleClientId | str,
    *,
    url: str,
    slug: str,
    password: str,
) -> str:
    if client_id not in CONSOLE_CLIENTS:
        raise ValueError(f"unknown console client: {client_id}")
    basic = basic_authorization(slug, password)
    if client_id == "claude_code":
        return (
            f"claude mcp add koicloud --transport http {url} "
            f'--header "Authorization: {basic}"'
        )
    if client_id == "cursor_cli":
        return json.dumps(
            {
                "mcpServers": {
                    "koicloud": {
                        "url": url,
                        "headers": {"Authorization": basic},
                    }
                }
            },
            indent=2,
        )
    return (
        "[mcp_servers.koicloud]\n"
        f'url = "{url}"\n'
        "\n"
        "[mcp_servers.koicloud.http_headers]\n"
        f'Authorization = "{basic}"\n'
    )


def headers_from_snippet(client_id: ConsoleClientId | str, snippet: str) -> dict[str, str]:
    """Extract the Authorization header a console client would send from its snippet."""
    if client_id not in CONSOLE_CLIENTS:
        raise ValueError(f"unknown console client: {client_id}")
    if client_id == "claude_code":
        match = re.search(r'--header "Authorization:\s*(Basic [^"]+)"', snippet)
        if match is None:
            raise ValueError("claude snippet missing Authorization header")
        return {"Authorization": match.group(1)}
    if client_id == "cursor_cli":
        payload = json.loads(snippet)
        headers = payload["mcpServers"]["koicloud"]["headers"]
        auth = headers.get("Authorization")
        if not isinstance(auth, str) or not auth.startswith("Basic "):
            raise ValueError("cursor snippet missing Authorization header")
        return {"Authorization": auth}
    match = re.search(r'Authorization\s*=\s*"(Basic [^"]+)"', snippet)
    if match is None:
        raise ValueError("codex snippet missing Authorization header")
    return {"Authorization": match.group(1)}
