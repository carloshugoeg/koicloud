"""HTTP shell for the preview sim. Domain rules live in state.py."""

from __future__ import annotations

import base64
import binascii
import json
import os
import pickle
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlsplit

from state import SimError, State, ToolMiss, User, same_secret

MAX_BODY = 1_000_000
STATE = State()
_PERSIST_LOADED = False
_BLOB_LOAD_OK = False
_LAST_BLOB_LOAD_AT = 0.0
# Reuse in-memory state across GETs on a warm instance; Blob list/get stampedes
# under Playwright parallel /me+/ponds and return empty → token_invalid.
_BLOB_RELOAD_SECONDS = 2.0


def _blob_token() -> str:
    return (os.environ.get("BLOB_READ_WRITE_TOKEN") or "").strip()


def _blob_key_base() -> str:
    # Prefer git branch so rolling alias deploys share one Blob (seed + SPA).
    raw = (
        os.environ.get("KOI_SIM_STATE_KEY")
        or os.environ.get("VERCEL_GIT_COMMIT_REF")
        or os.environ.get("VERCEL_DEPLOYMENT_ID")
        or "local"
    ).strip()
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in raw)[:80]


def _blob_path() -> str:
    # Bump generation when durable schema/guards change so rolling alias
    # instances on older builds cannot pollute the live Blob key.
    return f"koi-preview-sim-{_blob_key_base()}-v6.pkl"


def _users_blob_path() -> str:
    return f"koi-preview-sim-{_blob_key_base()}-v6-users.json"


def _persist_path() -> str:
    return (os.environ.get("KOI_SIM_PERSIST_PATH") or "").strip()


def _blob_find_url(token: str, pathname: str | None = None) -> str | None:
    target = pathname or _blob_path()
    query = urllib.parse.urlencode({"prefix": target, "limit": "10"})
    req = urllib.request.Request(
        f"https://blob.vercel-storage.com?{query}",
        headers={
            "Authorization": f"Bearer {token}",
            "x-api-version": "7",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    blobs = payload.get("blobs") if isinstance(payload, dict) else None
    if not isinstance(blobs, list) or not blobs:
        return None
    for item in blobs:
        if not isinstance(item, dict):
            continue
        pathname_found = item.get("pathname")
        url = item.get("url")
        if pathname_found == target and isinstance(url, str) and url:
            return url
    first = blobs[0]
    if not isinstance(first, dict):
        return None
    url = first.get("url")
    return url if isinstance(url, str) and url else None


def _download_blob_bytes(token: str, pathname: str) -> bytes | None:
    try:
        url = _blob_find_url(token, pathname)
        if not url:
            return None
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
        return raw or None
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        OSError,
    ):
        return None


def _put_blob_bytes(token: str, pathname: str, raw: bytes, content_type: str) -> bool:
    try:
        query = urllib.parse.urlencode({"pathname": pathname})
        req = urllib.request.Request(
            f"https://vercel.com/api/blob?{query}",
            data=raw,
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-version": "7",
                "x-content-type": content_type,
                "x-access": "private",
                "x-add-random-suffix": "0",
                "x-allow-overwrite": "1",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
        return True
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return False


def _read_blob_state_once(token: str) -> State | None:
    try:
        raw = _download_blob_bytes(token, _blob_path())
        if not raw:
            return None
        loaded = pickle.loads(raw)
        return loaded if isinstance(loaded, State) else None
    except (
        pickle.UnpicklingError,
        OSError,
        TypeError,
    ):
        return None


def _read_blob_state(token: str, *, attempts: int = 4) -> State | None:
    """Retry Blob list/get — concurrent cold starts otherwise miss seed state."""
    for attempt in range(max(1, attempts)):
        loaded = _read_blob_state_once(token)
        if loaded is not None:
            return loaded
        if attempt + 1 < attempts:
            time.sleep(0.15 * (attempt + 1))
    return None


def _users_to_json(state: State) -> bytes:
    rows = []
    for user in state.users_by_id.values():
        # Claim-hydrated stubs use password="" — never persist them or login breaks.
        if not user.password:
            continue
        rows.append(
            {
                "id": user.id,
                "email": user.email,
                "password": user.password,
                "full_name": user.full_name,
                "role": user.role,
                "status": user.status,
                "email_verified": user.email_verified,
                "nit": user.nit,
                "created_at": user.created_at,
            }
        )
    return json.dumps({"users": rows}, separators=(",", ":")).encode()


def _user_from_row(row: dict[str, object]) -> User | None:
    user_id = row.get("id")
    email = row.get("email")
    if not isinstance(user_id, str) or not isinstance(email, str):
        return None
    password = str(row.get("password") or "")
    if not password:
        return None
    return User(
        id=user_id,
        email=email.strip().lower(),
        password=password,
        full_name=str(row.get("full_name") or email),
        role=str(row.get("role") or "client"),
        status=str(row.get("status") or "active"),
        email_verified=bool(row.get("email_verified", True)),
        nit=row.get("nit") if isinstance(row.get("nit"), str) else None,
        created_at=str(row.get("created_at") or "2020-01-01T00:00:00Z"),
        verify_token=None,
    )


def _install_passworded_user(state: State, candidate: User, *, memory_wins: bool) -> None:
    """Install a passworded user. memory_wins=True ⇒ caller is the in-process reseed."""
    if not candidate.password:
        return
    prior = state.users_by_id.get(candidate.id) or state.users_by_email.get(candidate.email)
    if prior is None or not prior.password:
        chosen = candidate
    elif memory_wins:
        chosen = candidate
    elif same_secret(prior.password, candidate.password):
        chosen = _prefer_user(prior, candidate)
    else:
        # Sidecar hydrate into memory that already has a password (reseed) — keep memory.
        chosen = prior
    state.users_by_id[chosen.id] = chosen
    state.users_by_email[chosen.email] = chosen


def _merge_users_json(state: State, raw: bytes, *, memory_wins: bool = False) -> None:
    try:
        payload = json.loads(raw.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    rows = payload.get("users") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidate = _user_from_row(row)
        if candidate is None:
            continue
        _install_passworded_user(state, candidate, memory_wins=memory_wins)


def _load_users_sidecar(token: str, state: State) -> None:
    for attempt in range(4):
        raw = _download_blob_bytes(token, _users_blob_path())
        if raw:
            # Sidecar wins on cold hydrate so a wiped pickle cannot keep bad passwords.
            _merge_users_json(state, raw, memory_wins=False)
            return
        time.sleep(0.1 * (attempt + 1))


def _save_users_sidecar_union(token: str, state: State) -> bool:
    """Read-merge-write users.json so a partial instance cannot drop peers."""
    for attempt in range(6):
        existing = _download_blob_bytes(token, _users_blob_path())
        merged = State()
        if existing:
            _merge_users_json(merged, existing, memory_wins=False)
        before = _passworded_count(merged)
        for user in list(state.users_by_id.values()):
            if not user.password:
                continue
            _install_passworded_user(merged, user, memory_wins=True)
        raw = _users_to_json(merged)
        if _passworded_count(merged) < max(before, _passworded_count(state)) and attempt < 5:
            time.sleep(0.12 * (attempt + 1))
            continue
        if not _put_blob_bytes(token, _users_blob_path(), raw, "application/json"):
            time.sleep(0.12 * (attempt + 1))
            continue
        _merge_users_json(state, raw, memory_wins=False)
        return True
    return False

def _prefer_user(current: User | None, candidate: User) -> User:
    """Keep the durable passworded row over a claim-hydrated stub (password='')."""
    if current is None:
        return candidate
    if not current.password and candidate.password:
        return candidate
    if current.password and not candidate.password:
        return current
    # Same durability: prefer verified + active remote/candidate only when current is worse.
    if current.status != "active" and candidate.status == "active":
        return candidate
    if (not current.email_verified) and candidate.email_verified:
        return candidate
    return current


def _merge_state(writer: State, remote: State) -> None:
    """Union remote entities into writer so a stale instance cannot wipe peers."""
    for user_id, user in getattr(remote, "users_by_id", {}).items():
        chosen = _prefer_user(writer.users_by_id.get(user_id), user)
        writer.users_by_id[user_id] = chosen
        writer.users_by_email[chosen.email] = chosen
    for email, user in getattr(remote, "users_by_email", {}).items():
        chosen = _prefer_user(writer.users_by_email.get(email), user)
        writer.users_by_email[email] = chosen
        writer.users_by_id[chosen.id] = _prefer_user(writer.users_by_id.get(chosen.id), chosen)
    for attr in (
        "sessions",
        "subs",
        "ponds",
        "backups",
        "sql_events",
        "pending",
        "agents_by_user",
        "agents_by_slug",
    ):
        remote_map = getattr(remote, attr, None)
        writer_map = getattr(writer, attr, None)
        if not isinstance(remote_map, dict) or not isinstance(writer_map, dict):
            continue
        for key, value in remote_map.items():
            writer_map.setdefault(key, value)
    writer._next_port = max(
        int(getattr(writer, "_next_port", 0) or 0),
        int(getattr(remote, "_next_port", 0) or 0),
    )
    writer._invoice_n = max(
        int(getattr(writer, "_invoice_n", 0) or 0),
        int(getattr(remote, "_invoice_n", 0) or 0),
    )


def _strip_auth_stubs(state: State) -> None:
    """Drop claim-hydrated users (empty password) before Blob write."""
    for user_id, user in list(state.users_by_id.items()):
        if user.password:
            continue
        state.users_by_id.pop(user_id, None)
        mapped = state.users_by_email.get(user.email)
        if mapped is user or (mapped is not None and not mapped.password):
            state.users_by_email.pop(user.email, None)


def load_persisted_state(*, force: bool = False) -> None:
    """Hydrate STATE from Blob (preferred) or local file.

    Warm instances keep memory across GETs to avoid Blob stampedes. POSTs and
    empty/cold memory force a reload so seed/writes from peers are visible.
    """
    global STATE, _PERSIST_LOADED, _BLOB_LOAD_OK, _LAST_BLOB_LOAD_AT
    token = _blob_token()
    if token:
        now = time.monotonic()
        warm = bool(STATE.users_by_id) and _PERSIST_LOADED
        fresh = (now - _LAST_BLOB_LOAD_AT) < _BLOB_RELOAD_SECONDS
        if warm and fresh and not force:
            return
        loaded = _read_blob_state(token)
        if loaded is not None:
            if STATE.users_by_id and force:
                # Memory is writer: keep in-flight reseeds/mutations, pull peers from Blob.
                _merge_state(STATE, loaded)
            else:
                STATE = loaded
            _load_users_sidecar(token, STATE)
            _PERSIST_LOADED = True
            _BLOB_LOAD_OK = True
            _LAST_BLOB_LOAD_AT = now
            return
        # Pickle miss: still try the small users sidecar so HMAC auth can proceed.
        if not STATE.users_by_id:
            _load_users_sidecar(token, STATE)
            if STATE.users_by_id:
                _PERSIST_LOADED = True
                _BLOB_LOAD_OK = True
                _LAST_BLOB_LOAD_AT = now
                return
        # Keep in-memory STATE; never replace a populated warm cache with empty.
        _BLOB_LOAD_OK = False
        return
    if _PERSIST_LOADED:
        return
    _PERSIST_LOADED = True
    path = _persist_path()
    if not path:
        return
    try:
        with open(path, "rb") as handle:
            STATE = pickle.loads(handle.read())
    except (FileNotFoundError, pickle.UnpicklingError, OSError, EOFError):
        return


def _passworded_count(state: State) -> int:
    return sum(1 for user in state.users_by_id.values() if user.password)


def save_persisted_state() -> None:
    """Snapshot STATE so the next serverless instance can resume the gate seed."""
    global _BLOB_LOAD_OK, _LAST_BLOB_LOAD_AT
    token = _blob_token()
    if token:
        remote = _read_blob_state(token, attempts=4)
        if remote is not None:
            _merge_state(STATE, remote)
            _BLOB_LOAD_OK = True
        elif _BLOB_LOAD_OK:
            # Stampede miss after we have seen durable Blob — publishing partial
            # memory would drop peers registered on other instances.
            return
        elif not STATE.users_by_id:
            return
        _strip_auth_stubs(STATE)
        if _passworded_count(STATE) == 0:
            retry = _read_blob_state(token, attempts=4)
            if retry is None:
                return
            _merge_state(STATE, retry)
            _strip_auth_stubs(STATE)
            _BLOB_LOAD_OK = True
            if _passworded_count(STATE) == 0:
                return
            remote = retry
        # Never shrink the durable passworded user set (full-pickle replace).
        if remote is not None and _passworded_count(STATE) < _passworded_count(remote):
            # Still union the users sidecar — auth must survive pickle races.
            _save_users_sidecar_union(token, STATE)
            return
        raw = pickle.dumps(STATE, protocol=pickle.HIGHEST_PROTOCOL)
        wrote = _put_blob_bytes(token, _blob_path(), raw, "application/octet-stream")
        _save_users_sidecar_union(token, STATE)
        if wrote:
            _LAST_BLOB_LOAD_AT = time.monotonic()
            return
        # Blob PUT failed — do not fall through to a partial /tmp clobber.
        return
    path = _persist_path()
    if not path:
        return
    try:
        with open(path, "rb") as handle:
            disk = pickle.loads(handle.read())
        if isinstance(disk, State):
            _merge_state(STATE, disk)
    except (FileNotFoundError, pickle.UnpicklingError, OSError, EOFError):
        disk = None
    _strip_auth_stubs(STATE)
    if _passworded_count(STATE) == 0:
        return
    if isinstance(disk, State) and _passworded_count(STATE) < _passworded_count(disk):
        return
    raw = pickle.dumps(STATE, protocol=pickle.HIGHEST_PROTOCOL)
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary = f"{path}.tmp"
        with open(temporary, "wb") as handle:
            handle.write(raw)
        os.replace(temporary, path)
    except OSError:
        return

HandlerFn = Callable[
    [State, dict[str, str], dict[str, str], bytes],
    tuple[int, dict[str, object] | None],
]


def _json_dict(raw: bytes) -> dict[str, object]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SimError("token_invalid", message="JSON inválido") from exc
    if not isinstance(data, dict):
        raise SimError("token_invalid", message="JSON inválido")
    return data


def _need_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise SimError("token_invalid", message="Solicitud inválida")
    return value


def _bearer(state: State, headers: dict[str, str]) -> str:
    header = headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise SimError("token_invalid")
    token = header.split(" ", 1)[1].strip()
    if not token:
        raise SimError("token_invalid")
    return state.user_id_for_token(token)


def _basic(headers: dict[str, str]) -> tuple[str, str]:
    header = headers.get("authorization", "")
    if not header.lower().startswith("basic "):
        raise SimError("agent_bad_credentials")
    encoded = header.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        slug, password = decoded.split(":", 1)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise SimError("agent_bad_credentials") from exc
    if not slug or not password:
        raise SimError("agent_bad_credentials")
    return slug, password


def _base_url(headers: dict[str, str]) -> str:
    # Prefer the public preview origin so agent-access / MCP URLs match the
    # Vercel host under test (not the loopback sim listen address).
    public = (os.environ.get("KOI_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if public:
        return public
    host = headers.get("host", "127.0.0.1:18080")
    scheme = "https" if host.endswith(".vercel.app") else "http"
    return f"{scheme}://{host}"


def route_health(
    _state: State,
    _groups: dict[str, str],
    _headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    sha = (os.environ.get("VERCEL_GIT_COMMIT_SHA") or "").strip() or "sim-backend"
    return 200, {"ok": True, "git_sha": sha, "sim": True}


def route_register(
    state: State,
    _groups: dict[str, str],
    _headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    nit = data.get("nit")
    status, payload = state.register(
        email=_need_str(data, "email"),
        password=_need_str(data, "password"),
        full_name=_need_str(data, "full_name"),
        nit=nit if isinstance(nit, str) else None,
    )
    # Flush users sidecar before the response so the next cold login sees the password.
    blob = _blob_token()
    if blob:
        _save_users_sidecar_union(blob, STATE)
    return status, payload


def route_verify(
    state: State,
    _groups: dict[str, str],
    _headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    token = _need_str(data, "token")
    blob = _blob_token()
    if not blob:
        return 200, state.verify(token)
    load_persisted_state(force=True)
    _load_users_sidecar(blob, STATE)
    try:
        return 200, STATE.verify(token)
    except SimError as exc:
        if exc.code != "token_invalid":
            raise
        time.sleep(0.2)
        load_persisted_state(force=True)
        _load_users_sidecar(blob, STATE)
        return 200, STATE.verify(token)


def route_login(
    state: State,
    _groups: dict[str, str],
    _headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    email = _need_str(data, "email")
    password = _need_str(data, "password")
    # Always rehydrate from the merge-only users sidecar before checking the password.
    blob = _blob_token()
    if blob:
        load_persisted_state(force=True)
        _load_users_sidecar(blob, STATE)
    try:
        return 200, STATE.login(email, password)
    except SimError as exc:
        if exc.code != "invalid_credentials" or not blob:
            raise
        time.sleep(0.2)
        load_persisted_state(force=True)
        _load_users_sidecar(blob, STATE)
        return 200, STATE.login(email, password)


def route_plans(
    state: State,
    _groups: dict[str, str],
    _headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.plans()


def route_me(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.me(_bearer(state, headers))


def route_subscribe(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    return 202, state.subscribe(_bearer(state, headers), _need_str(data, "plan_id"))


def route_subscriptions(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.list_subscriptions(_bearer(state, headers))


def route_pond_create(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    engine = data.get("engine_version")
    engine_version = engine if isinstance(engine, str) and engine else "16"
    return 202, state.create_pond(
        _bearer(state, headers),
        _need_str(data, "name"),
        engine_version,
    )


def route_pond_list(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.list_ponds(_bearer(state, headers))


def route_pond_get(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.get_pond(_bearer(state, headers), groups["pond_id"])


def route_connection(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.connection(_bearer(state, headers), groups["pond_id"])


def route_stop(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.apply_pond(_bearer(state, headers), groups["pond_id"], "stop")


def route_start(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.apply_pond(_bearer(state, headers), groups["pond_id"], "start")


def route_backup_create(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 202, state.trigger_backup(_bearer(state, headers), groups["pond_id"])


def route_backup_list(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.list_backups(_bearer(state, headers), groups["pond_id"])


def route_sql(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    mode = data.get("mode")
    mode_text = mode if isinstance(mode, str) and mode else "read"
    return 200, state.run_sql(
        _bearer(state, headers),
        groups["pond_id"],
        _need_str(data, "query"),
        mode_text,
    )


def route_sql_history(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.list_sql_history(_bearer(state, headers), groups["pond_id"])


def route_admin_ponds(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.list_admin_ponds(_bearer(state, headers))


def route_pond_delete(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    user_id = _bearer(state, headers)
    token = headers.get("x-koi-confirm-token", "").strip()
    if token:
        _action, payload = state.confirm(user_id, token, expect="delete_pond")
        return 202, payload
    return 409, state.delete_pond(user_id, groups["pond_id"])


def route_confirm(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    action, payload = state.confirm(_bearer(state, headers), groups["token"])
    status = 200 if action == "run_sql" else 202
    return status, payload


def route_cancel(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, None]:
    state.cancel(_bearer(state, headers), groups["token"])
    return 204, None


def route_admin_users(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.list_admin_users(_bearer(state, headers))


def route_usage(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    from urllib.parse import parse_qs

    params = parse_qs(headers.get("x-koi-raw-query", ""))
    values = params.get("month") or []
    month = values[0] if values else None
    return 200, state.usage(_bearer(state, headers), month)


def route_suspend(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    return 200, state.suspend(
        _bearer(state, headers),
        groups["user_id"],
        _need_str(data, "confirm_text"),
    )


def route_reactivate(
    state: State,
    groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.reactivate(_bearer(state, headers), groups["user_id"])


def route_agent_get(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.agent_get(_bearer(state, headers), _base_url(headers))


def route_agent_rotate(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    return 200, state.agent_rotate(_bearer(state, headers), _base_url(headers))


def route_agent_toggle(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object]]:
    data = _json_dict(body)
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise SimError("token_invalid", message="Solicitud inválida")
    return 200, state.agent_toggle(_bearer(state, headers), enabled)


def _tool_error(name: str, exc: SimError) -> dict[str, object]:
    text = exc.message
    return {
        "content": [{"type": "text", "text": f"Error calling tool '{name}': {text}"}],
        "structuredContent": {"code": exc.code, "message": text},
        "isError": True,
    }


def _split_tool(method: str, params: dict[str, object]) -> tuple[str, dict[str, object]]:
    if method in {"tools/call", "call_tool"}:
        raw_name = params.get("name") or params.get("tool") or ""
        raw_args = params.get("arguments")
        if raw_args is None:
            raw_args = params.get("params")
        args = raw_args if isinstance(raw_args, dict) else {}
        return str(raw_name), args
    return method, params


def route_mcp_get(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    _body: bytes,
) -> tuple[int, dict[str, object]]:
    slug, password = _basic(headers)
    state.mcp_user(slug, password)
    return 200, state.mcp_info()


def route_mcp_post(
    state: State,
    _groups: dict[str, str],
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object] | None]:
    slug, password = _basic(headers)
    user_id = state.mcp_user(slug, password)
    if not body:
        raise SimError("token_invalid", message="JSON inválido")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SimError("token_invalid", message="JSON inválido") from exc
    if not isinstance(payload, dict):
        raise SimError("token_invalid", message="JSON inválido")
    method = payload.get("method")
    if not isinstance(method, str) or not method:
        raise SimError("token_invalid", message="JSON inválido")
    params_raw = payload.get("params") or {}
    params = params_raw if isinstance(params_raw, dict) else {}
    rpc_id = payload.get("id")
    if method.startswith("notifications/"):
        return 202, None
    if method == "initialize":
        version = params.get("protocolVersion")
        protocol = version if isinstance(version, str) and version else "2024-11-05"
        result: dict[str, object] = {
            "protocolVersion": protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "KoiCloud", "version": "sim"},
        }
        return 200, {"jsonrpc": "2.0", "id": rpc_id, "result": result, "error": None}
    if method in {"tools/list", "list_tools"}:
        result = state.tool_catalog()
        return 200, {"jsonrpc": "2.0", "id": rpc_id, "result": result, "error": None}
    if method == "ping":
        return 200, {"jsonrpc": "2.0", "id": rpc_id, "result": {}, "error": None}
    name, args = _split_tool(method, params)
    if not name:
        missed = _tool_error(
            "tools/call",
            SimError("method_not_found", message="tool name required"),
        )
        return 200, {"jsonrpc": "2.0", "id": rpc_id, "result": missed, "error": None}
    try:
        result = state.mcp_call(user_id, name, args)
    except ToolMiss as exc:
        missed = _tool_error(
            exc.name,
            SimError("method_not_found", message=f"unknown tool '{exc.name}'"),
        )
        return 200, {"jsonrpc": "2.0", "id": rpc_id, "result": missed, "error": None}
    except SimError as exc:
        return 200, {"jsonrpc": "2.0", "id": rpc_id, "result": _tool_error(name, exc), "error": None}
    return 200, {"jsonrpc": "2.0", "id": rpc_id, "result": result, "error": None}


ROUTES: list[tuple[str, re.Pattern[str], HandlerFn]] = [
    ("GET", re.compile(r"^/api/v1/health$"), route_health),
    ("POST", re.compile(r"^/api/v1/auth/register$"), route_register),
    ("POST", re.compile(r"^/api/v1/auth/verify$"), route_verify),
    ("POST", re.compile(r"^/api/v1/auth/login$"), route_login),
    ("GET", re.compile(r"^/api/v1/plans$"), route_plans),
    ("GET", re.compile(r"^/api/v1/me$"), route_me),
    ("POST", re.compile(r"^/api/v1/subscriptions$"), route_subscribe),
    ("GET", re.compile(r"^/api/v1/subscriptions$"), route_subscriptions),
    ("POST", re.compile(r"^/api/v1/ponds$"), route_pond_create),
    ("GET", re.compile(r"^/api/v1/ponds$"), route_pond_list),
    ("POST", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)/stop$"), route_stop),
    ("POST", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)/start$"), route_start),
    ("POST", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)/backups$"), route_backup_create),
    ("GET", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)/backups$"), route_backup_list),
    ("POST", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)/sql$"), route_sql),
    ("GET", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)/sql/history$"), route_sql_history),
    ("GET", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)/connection$"), route_connection),
    ("GET", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)$"), route_pond_get),
    ("DELETE", re.compile(r"^/api/v1/ponds/(?P<pond_id>[^/]+)$"), route_pond_delete),
    ("POST", re.compile(r"^/api/v1/confirm/(?P<token>[^/]+)$"), route_confirm),
    ("DELETE", re.compile(r"^/api/v1/confirm/(?P<token>[^/]+)$"), route_cancel),
    ("GET", re.compile(r"^/api/v1/admin/users$"), route_admin_users),
    ("GET", re.compile(r"^/api/v1/admin/ponds$"), route_admin_ponds),
    ("POST", re.compile(r"^/api/v1/admin/users/(?P<user_id>[^/]+)/suspend$"), route_suspend),
    ("POST", re.compile(r"^/api/v1/admin/users/(?P<user_id>[^/]+)/reactivate$"), route_reactivate),
    ("GET", re.compile(r"^/api/v1/usage$"), route_usage),
    ("GET", re.compile(r"^/api/v1/agent-access$"), route_agent_get),
    ("POST", re.compile(r"^/api/v1/agent-access/rotate$"), route_agent_rotate),
    ("POST", re.compile(r"^/api/v1/agent-access/toggle$"), route_agent_toggle),
    ("GET", re.compile(r"^/mcp$"), route_mcp_get),
    ("POST", re.compile(r"^/mcp$"), route_mcp_post),
]


def dispatch(
    method: str,
    path: str,
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, dict[str, object] | None]:
    # POST/DELETE must see peer writes (seed, login). GETs reuse warm memory.
    load_persisted_state(force=method not in {"GET", "OPTIONS", "HEAD"})
    if method == "OPTIONS":
        return 204, None
    for route_method, pattern, handler in ROUTES:
        if route_method != method:
            continue
        match = pattern.match(path)
        if match is None:
            continue
        try:
            result = handler(STATE, match.groupdict(), headers, body)
        except SimError as exc:
            # Valid HMAC but missing user usually means a stale/empty load — refresh once.
            if exc.code == "token_invalid" and method in {"GET", "HEAD"}:
                load_persisted_state(force=True)
                result = handler(STATE, match.groupdict(), headers, body)
            else:
                raise
        if method != "GET":
            save_persisted_state()
        return result
    raise SimError("pond_not_found", status=404, message="Ruta no encontrada")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        # Confirm tokens sit in the path. Do not write the request line.
        return

    def _read_body(self) -> bytes:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            length = 0
        if length < 0 or length > MAX_BODY:
            raise SimError("token_invalid", message="Solicitud inválida")
        if length == 0:
            return b""
        return self.rfile.read(length)

    def _serve(self) -> None:
        try:
            body = self._read_body()
            headers = {key.lower(): value for key, value in self.headers.items()}
            split = urlsplit(self.path)
            path = split.path
            headers["x-koi-raw-query"] = split.query
            status, payload = dispatch(self.command, path, headers, body)
        except SimError as exc:
            status = exc.status
            payload = exc.body()
        except Exception as exc:
            sys.stderr.write(f"sim error {type(exc).__name__}\n")
            status = 500
            payload = {
                "code": "internal_error",
                "message": "Algo salió mal, revisá los logs",
                "request_id": None,
            }
        self._send(status, payload)

    def _send(self, status: int, payload: dict[str, object] | None) -> None:
        raw = b"" if payload is None else json.dumps(payload).encode()
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type, X-KOI-Surface, X-KOI-Confirm-Token, "
            "X-KOI-Agent-Password, Idempotency-Key, Accept, MCP-Protocol-Version, "
            "Mcp-Session-Id",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        if self.command == "POST" and urlsplit(self.path).path == "/mcp":
            session = self.headers.get("Mcp-Session-Id") or "sim-session"
            self.send_header("Mcp-Session-Id", session)
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def do_GET(self) -> None:
        self._serve()

    def do_POST(self) -> None:
        self._serve()

    def do_DELETE(self) -> None:
        self._serve()

    def do_OPTIONS(self) -> None:
        self._serve()


def main() -> None:
    host = os.environ.get("KOI_SIM_HOST", "127.0.0.1")
    port = int(os.environ.get("KOI_SIM_PORT", "18080"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"sim listening http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
