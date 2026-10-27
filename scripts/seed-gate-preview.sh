#!/usr/bin/env bash
# Idempotent gate seed for the local sim.
# Refuses hosts other than localhost, 127.0.0.1, and *.test.
# Also refuses production markers in the host.
# Writes passwords only when KOI_GATE_CREDENTIALS_OUT is an absolute path.
set -euo pipefail

python3 - <<'PY'
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ADMIN_EMAIL = "gate-admin@koicloud.test"
USER_EMAIL = "gate-user@koicloud.test"
PROD_MARKERS = ("koicloud.dev", "vercel.app", "koicloud.com")


def fail(message: str, code: int) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def classify(url: str) -> str:
    if not url.strip():
        return "empty"
    parsed = urllib.parse.urlparse(url.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not host:
        return "host"
    if any(marker in host for marker in PROD_MARKERS):
        return "prod"
    if host in {"localhost", "127.0.0.1"} or host.endswith(".test"):
        return "ok"
    return "host"


def canonical(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host}{port}"


def request(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
    basic: str | None = None,
):
    url = base + path
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    if basic:
        encoded = base64.b64encode(basic.encode()).decode("ascii")
        headers["Authorization"] = "Basic " + encoded
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode()
            parsed = json.loads(raw) if raw else {}
            if not isinstance(parsed, dict):
                return res.status, {"code": "http_error"}
            return res.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"code": "http_error"}
        if not isinstance(parsed, dict):
            parsed = {"code": "http_error"}
        return exc.code, parsed
    except urllib.error.URLError:
        fail("seed failed unreachable", 1)


def code_of(payload: dict) -> str:
    value = payload.get("code")
    return value if isinstance(value, str) else "http_error"


def ensure_user(base: str, email: str, password: str, full_name: str) -> str:
    status, body = request(
        base,
        "POST",
        "/api/v1/auth/register",
        {"email": email, "password": password, "full_name": full_name},
    )
    if status == 409 and code_of(body) == "email_taken":
        # Idempotent re-seed: same email already present. Login must work with
        # the password from KOI_GATE_CREDENTIALS_OUT (or this run's draft).
        lstatus, login = request(
            base,
            "POST",
            "/api/v1/auth/login",
            {"email": email, "password": password},
        )
        if lstatus == 200 and isinstance(login.get("access_token"), str):
            access = login["access_token"]
            sstatus, _sub = request(
                base,
                "POST",
                "/api/v1/subscriptions",
                {"plan_id": "pro"},
                token=access,
            )
            if sstatus not in {200, 201, 202}:
                fail("seed failed", 1)
            return access
        fail("seed conflict", 3)
    if status not in {200, 201}:
        fail("seed failed", 1)
    if body.get("email_verified") is not True:
        token = body.get("verify_token")
        if not isinstance(token, str) or not token:
            fail("seed failed", 1)
        vstatus, vbody = request(base, "POST", "/api/v1/auth/verify", {"token": token})
        if vstatus != 200 or vbody.get("email_verified") is not True:
            fail("seed failed", 1)
    lstatus, login = request(
        base,
        "POST",
        "/api/v1/auth/login",
        {"email": email, "password": password},
    )
    if lstatus != 200 or not isinstance(login.get("access_token"), str):
        fail("seed failed", 1)
    access = login["access_token"]
    sstatus, _sub = request(
        base,
        "POST",
        "/api/v1/subscriptions",
        {"plan_id": "pro"},
        token=access,
    )
    if sstatus not in {200, 201, 202}:
        fail("seed failed", 1)
    return access


def load_record(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        fail("seed failed", 1)
    if not isinstance(data, dict):
        fail("seed failed", 1)
    return data


def secret_from(record: dict | None, section: str) -> str | None:
    if not record:
        return None
    block = record.get(section)
    if not isinstance(block, dict):
        return None
    value = block.get("password")
    if isinstance(value, str) and len(value) >= 8:
        return value
    return None


def mcp_from(record: dict | None) -> tuple[str | None, str | None]:
    if not record:
        return None, None
    block = record.get("mcp")
    if not isinstance(block, dict):
        return None, None
    slug = block.get("slug")
    password = block.get("password")
    expires = block.get("expires_at")
    if not isinstance(slug, str) or not isinstance(password, str) or len(password) < 8:
        return None, None
    if not isinstance(expires, str):
        return slug, None
    return slug, password


def write_record(path: str, payload: dict) -> None:
    parent = os.path.dirname(path)
    os.makedirs(parent, mode=0o700, exist_ok=True)
    temporary = path + ".part"
    raw = json.dumps(payload, indent=2, sort_keys=True).encode() + b"\n"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def mcp_alive(base: str, slug: str, password: str) -> int:
    status, body = request(base, "GET", "/mcp", basic=f"{slug}:{password}")
    if status == 403 and code_of(body) == "agent_disabled":
        return 403
    return status


def main() -> None:
    os.umask(0o077)
    raw_url = os.environ.get("KOI_SIM_BASE_URL", "")
    kind = classify(raw_url)
    if kind == "empty":
        fail("refused empty", 2)
    if kind == "prod":
        fail("refused prod", 2)
    if kind != "ok":
        fail("refused host", 2)
    base = canonical(raw_url)

    out = os.environ.get("KOI_GATE_CREDENTIALS_OUT", "").strip()
    if out and not os.path.isabs(out):
        fail("refused credentials path", 2)

    record = load_record(out) if out else None
    admin_password = secret_from(record, "admin")
    user_password = secret_from(record, "user")
    if admin_password is None:
        admin_password = secrets_token()
    if user_password is None:
        user_password = secrets_token()

    draft = {
        "base_url": base,
        "admin": {"email": ADMIN_EMAIL, "password": admin_password},
        "user": {"email": USER_EMAIL, "password": user_password},
        "mcp": record.get("mcp") if record and isinstance(record.get("mcp"), dict) else None,
    }
    if out:
        write_record(out, draft)

    ensure_user(base, ADMIN_EMAIL, admin_password, "Gate Admin")
    user_access = ensure_user(base, USER_EMAIL, user_password, "Gate User")

    slug, mcp_password = mcp_from(draft)
    reuse = False
    if slug and mcp_password:
        alive = mcp_alive(base, slug, mcp_password)
        if alive == 200:
            reuse = True
        elif alive == 403:
            tstatus, _toggle = request(
                base,
                "POST",
                "/api/v1/agent-access/toggle",
                {"enabled": True},
                token=user_access,
            )
            if tstatus == 200 and mcp_alive(base, slug, mcp_password) == 200:
                reuse = True
    if not reuse:
        rstatus, rotated = request(
            base,
            "POST",
            "/api/v1/agent-access/rotate",
            {},
            token=user_access,
        )
        if rstatus != 200:
            fail("seed failed", 1)
        slug = rotated.get("slug")
        mcp_password = rotated.get("password")
        expires = rotated.get("expires_at")
        url = rotated.get("url")
        if not isinstance(slug, str) or not isinstance(mcp_password, str):
            fail("seed failed", 1)
        if not isinstance(expires, str):
            expires = ""
        if not isinstance(url, str) or not url:
            url = base + "/mcp"
        draft["mcp"] = {
            "slug": slug,
            "password": mcp_password,
            "expires_at": expires,
            "url": url,
        }
    if out:
        write_record(out, draft)

    mcp = draft.get("mcp")
    if not isinstance(mcp, dict):
        fail("seed failed", 1)
    if not isinstance(mcp.get("password"), str) or len(mcp["password"]) < 8:
        fail("seed failed", 1)
    if not isinstance(mcp.get("expires_at"), str) or not mcp["expires_at"]:
        fail("seed failed", 1)

    preview = os.environ.get("PLAYWRIGHT_BASE_URL", "").strip()
    if preview and out:
        draft["preview_url"] = preview
        draft["sim_base_url"] = base
        draft["mock_backend_steps"] = [
            "cd e2e/sim-backend && python3 -m app",
            "export KOI_SIM_BASE_URL=http://127.0.0.1:18080",
            "export KOI_GATE_CREDENTIALS_OUT=<absolute store credentials path>",
            "bash scripts/seed-gate-preview.sh",
            "cd e2e/preview && pnpm install && pnpm exec playwright install chromium && pnpm test",
            "python3 e2e/preview/mcp_client_suite.py",
        ]
        # Shape also accepted by e2e/preview creds.ts users.* keys.
        draft["users"] = {
            "admin": draft["admin"],
            "user": draft["user"],
        }
        write_record(out, draft)

    print("seeded")
    print(ADMIN_EMAIL)
    print(USER_EMAIL)
    if out:
        print(out)
    else:
        print("credentials not written")


def secrets_token() -> str:
    import secrets

    return secrets.token_urlsafe(18)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        fail("seed failed", 1)
PY
