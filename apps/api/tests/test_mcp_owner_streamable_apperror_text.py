"""Owner Streamable HTTP must keep main's AppError exception text.

TEMP-CONFIRM (issue #96 CCR) does not redesign legacy owner Streamable wire.
FastMCP Streamable ToolError envelopes expose ``str(exception)`` only.
On main, ``AppError`` uses the catalog Spanish message as that string.
"""

from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import ERROR_CATALOG, AppError, ErrorCode
from app.main import app
from tests.db_reset import ensure_demo_user

STREAM_ACCEPT = "application/json, text/event-stream"

# Codes that owner Streamable paths commonly surface as ToolError text.
_OWNER_STREAMABLE_CODES = (
    ErrorCode.CONFIRMATION_NOT_FOUND,
    ErrorCode.CONFIRMATION_EXPIRED,
    ErrorCode.CONFIRMATION_ACTION_MISMATCH,
    ErrorCode.AGENT_DISABLED,
    ErrorCode.POND_NOT_FOUND,
)


def test_apperror_exception_text_is_catalog_message_only() -> None:
    """Streamable serializes ``str(AppError)``; keep it catalog Spanish, as on main."""
    for code in _OWNER_STREAMABLE_CODES:
        err = AppError(code)
        expected = ERROR_CATALOG[code].message
        assert str(err) == expected, (code, str(err), expected)
        assert err.message == expected
        assert not str(err).startswith(f"{code.value}:")


def _parse_sse_messages(raw: str) -> list[dict]:
    messages: list[dict] = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                messages.append(json.loads(line[5:].strip()))
    return messages


def _owner_mcp_headers() -> dict[str, str]:
    settings = get_settings()
    token = base64.b64encode(
        f"{settings.mcp_demo_slug}:{settings.mcp_demo_password}".encode()
    ).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_owner_streamable_tool_error_text_matches_main_catalog_message() -> None:
    """Owner Streamable confirm_action ToolError text matches main (catalog only)."""
    ensure_demo_user()
    catalog = ERROR_CATALOG[ErrorCode.CONFIRMATION_NOT_FOUND].message
    # FastMCP prefixes ToolError text; AppError contributes only the catalog message on main.
    expected = f"Error calling tool 'confirm_action': {catalog}"
    forbidden = f"{ErrorCode.CONFIRMATION_NOT_FOUND.value}: {catalog}"

    with TestClient(app) as stream_client:
        response = stream_client.post(
            "/mcp",
            headers={
                **_owner_mcp_headers(),
                "Accept": STREAM_ACCEPT,
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "confirm_action",
                    "arguments": {"token": "conf-not-a-real-token"},
                },
            },
        )

    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers.get("content-type", "")
    messages = _parse_sse_messages(response.text)
    assert messages, response.text
    result = messages[-1].get("result") or {}
    assert result.get("isError") is True, messages[-1]
    text_bits = [
        part.get("text", "")
        for part in result.get("content") or []
        if isinstance(part, dict)
    ]
    joined = " ".join(text_bits).strip()
    assert joined == expected, (joined, expected)
    assert forbidden not in joined
