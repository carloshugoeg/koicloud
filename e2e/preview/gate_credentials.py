"""Read the gate credentials file without echoing secret fields."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

STORE_CREDS = Path(
    "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/gate-access/credentials.json"
)


@dataclass(frozen=True)
class Account:
    email: str
    password: str


@dataclass(frozen=True)
class McpAccount:
    slug: str
    password: str


@dataclass(frozen=True)
class GateCreds:
    admin: Account
    user: Account
    mcp: McpAccount


def credentials_path() -> Path:
    raw = os.environ.get("KOI_GATE_CREDENTIALS_OUT")
    if raw:
        return Path(raw)
    return STORE_CREDS


def load_gate() -> GateCreds:
    path = credentials_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise SystemExit("gate credentials file is missing or unreadable") from None
    creds = _parse(payload)
    if creds is None:
        raise SystemExit("gate credentials file is missing admin, user, or mcp fields")
    return creds


def _parse(payload: object) -> GateCreds | None:
    root = _record(payload)
    if root is None:
        return None
    users = _record(root.get("users")) or root
    admin = (
        _account(users.get("admin"))
        or _account(users.get("gate-admin"))
        or _account(root.get("admin"))
        or _account_by_role(root, "admin")
    )
    user = (
        _account(users.get("user"))
        or _account(users.get("client"))
        or _account(users.get("gate-user"))
        or _account(root.get("user"))
        or _account(root.get("client"))
        or _account_by_role(root, "client")
    )
    mcp = _mcp(root.get("mcp")) or _mcp(root.get("agent")) or _mcp_flat(root)
    if admin is None or user is None or mcp is None:
        return None
    return GateCreds(admin=admin, user=user, mcp=mcp)


def _account(value: object) -> Account | None:
    rec = _record(value)
    if rec is None:
        return None
    email = _text(rec.get("email"))
    password = _text(rec.get("password"))
    if email is None or password is None:
        return None
    return Account(email=email, password=password)


def _mcp(value: object) -> McpAccount | None:
    rec = _record(value)
    if rec is None:
        return None
    slug = _text(rec.get("slug"))
    password = _text(rec.get("password")) or _text(rec.get("agent_password"))
    if slug is None or password is None:
        return None
    return McpAccount(slug=slug, password=password)


def _mcp_flat(root: dict[str, object]) -> McpAccount | None:
    slug = _text(root.get("mcp_slug")) or _text(root.get("slug"))
    password = _text(root.get("mcp_password")) or _text(root.get("agent_password"))
    if slug is None or password is None:
        return None
    return McpAccount(slug=slug, password=password)


def _account_by_role(root: dict[str, object], role: str) -> Account | None:
    listed = root.get("accounts")
    if not isinstance(listed, list):
        listed = root.get("users")
    if not isinstance(listed, list):
        return None
    for item in listed:
        rec = _record(item)
        if rec is None or _text(rec.get("role")) != role:
            continue
        found = _account(rec)
        if found is not None:
            return found
    return None


def _record(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return value


def _text(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
