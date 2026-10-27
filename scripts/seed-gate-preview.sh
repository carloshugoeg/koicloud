#!/usr/bin/env bash
# Idempotent gate seed for the preview sim (loopback or hosted preview).
# Allows localhost, 127.0.0.1, and *.test.
# With KOI_ALLOW_PREVIEW_SEED=1, also allows non-production *.vercel.app hosts.
# Always refuses koicloud.dev, koicloud.com, and production Vercel aliases.
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
PROD_MARKERS = ("koicloud.dev", "koicloud.com")
PROD_VERCEL_HOSTS = {
    "koicloud-web.vercel.app",
    "koicloud-web-hugos-projects-3379fa36.vercel.app",
}


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
    if host.endswith(".vercel.app"):
        allow = os.environ.get("KOI_ALLOW_PREVIEW_SEED", "").strip() == "1"
        if not allow:
            return "prod"
        if host in PROD_VERCEL_HOSTS or "-git-main-" in host:
            return "prod"
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
    last_url_error = None
    # Hosted Vercel Blob cold paths often take 15–40s; 30s caused TimeoutError
    # that escaped URLError handling and aborted the whole seed.
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as res:
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
            # Retry cold-start / overload from the hosted sim.
            if exc.code in {425, 429, 500, 502, 503, 504} and attempt < 5:
                import time
                time.sleep(1.5 * (attempt + 1))
                continue
            return exc.code, parsed
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_url_error = exc
            import time
            time.sleep(1.5 * (attempt + 1))
    fail("seed failed unreachable", 1)


def code_of(payload: dict) -> str:
    value = payload.get("code")
    return value if isinstance(value, str) else "http_error"


def seed_fail(step: str, status: int, body: dict) -> None:
    code = code_of(body)
    print(f"seed failed step={step} status={status} code={code}", file=sys.stderr)
    raise SystemExit(1)


def login_with_retry(base: str, email: str, password: str) -> tuple[str | None, int, dict]:
    import time

    last_status, last_body = 0, {}
    for attempt in range(10):
        last_status, last_body = request(
            base,
            "POST",
            "/api/v1/auth/login",
            {"email": email, "password": password},
        )
        if last_status == 200 and isinstance(last_body.get("access_token"), str):
            return last_body["access_token"], last_status, last_body
        # Blob lag after register/reseed on a cold preview instance.
        if last_status in {401, 403, 404, 425, 429, 500, 502, 503, 504} and attempt < 9:
            time.sleep(0.8 * (attempt + 1))
            continue
        break
    return None, last_status, last_body if isinstance(last_body, dict) else {}


def ensure_user(base: str, email: str, password: str, full_name: str) -> str:
    """Upsert gate user, then prove login against the same base URL before continuing."""
    import time

    last_status, last_body = 0, {}
    for round_i in range(8):
        status, body = request(
            base,
            "POST",
            "/api/v1/auth/register",
            {"email": email, "password": password, "full_name": full_name},
        )
        last_status, last_body = status, body
        if status == 409 and code_of(body) == "email_taken":
            # Host without preview reseed — keep trying login with our password.
            pass
        elif status not in {200, 201}:
            if round_i < 7:
                time.sleep(0.8 * (round_i + 1))
                continue
            seed_fail("register", status, body)
        elif body.get("email_verified") is not True:
            token = body.get("verify_token")
            if not isinstance(token, str) or not token:
                if round_i < 7:
                    time.sleep(0.8 * (round_i + 1))
                    continue
                seed_fail("verify_token", status, body)
            verified = False
            for attempt in range(6):
                vstatus, vbody = request(base, "POST", "/api/v1/auth/verify", {"token": token})
                if vstatus == 200 and vbody.get("email_verified") is True:
                    verified = True
                    break
                time.sleep(0.8 * (attempt + 1))
            if not verified and round_i < 7:
                time.sleep(0.8 * (round_i + 1))
                continue
            if not verified:
                seed_fail("verify", vstatus, vbody if isinstance(vbody, dict) else {})

        access, lstatus, lbody = login_with_retry(base, email, password)
        if access is None:
            # Password did not stick on every instance — upsert again.
            time.sleep(0.8 * (round_i + 1))
            continue
        # Skip subscribe when an active plan already exists (idempotent seed).
        mestatus, mebody = request(base, "GET", "/api/v1/me", token=access)
        if mestatus == 200 and isinstance(mebody.get("subscription"), dict):
            return access
        sstatus, sub = request(
            base,
            "POST",
            "/api/v1/subscriptions",
            {"plan_id": "pro"},
            token=access,
        )
        if sstatus not in {200, 201, 202}:
            # Auth worked; subscription may race — retry upsert round.
            time.sleep(0.8 * (round_i + 1))
            last_status, last_body = sstatus, sub
            continue
        return access
    seed_fail("login", last_status, last_body if isinstance(last_body, dict) else {})
    raise SystemExit(1)


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


def mcp_initialize_ok(base: str, slug: str, password: str) -> bool:
    """Prove JSON-RPC initialize (Accept: application/json) before CI MCP suite."""
    import time

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "gate-seed", "version": "0"},
        },
    }
    for attempt in range(8):
        status, body = request(base, "POST", "/mcp", payload, basic=f"{slug}:{password}")
        result = body.get("result") if isinstance(body, dict) else None
        server = result.get("serverInfo") if isinstance(result, dict) else None
        if (
            status == 200
            and isinstance(server, dict)
            and server.get("name") == "KoiCloud"
        ):
            return True
        if status in {401, 403, 425, 429, 500, 502, 503, 504} and attempt < 7:
            time.sleep(0.8 * (attempt + 1))
            continue
        break
    return False


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
    # Deterministic preview-sim fixtures so every CI run reseeds the same Blob rows.
    # Override with KOI_GATE_*_PASSWORD; never print these values.
    preview_seed = os.environ.get("KOI_ALLOW_PREVIEW_SEED", "").strip() == "1"
    admin_password = (
        os.environ.get("KOI_GATE_ADMIN_PASSWORD", "").strip()
        or secret_from(record, "admin")
        or ("KoiGateAdmin!preview-sim-v5" if preview_seed else None)
        or secrets_token()
    )
    user_password = (
        os.environ.get("KOI_GATE_USER_PASSWORD", "").strip()
        or secret_from(record, "user")
        or ("KoiGateUser!preview-sim-v5" if preview_seed else None)
        or secrets_token()
    )

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
            seed_fail("rotate", rstatus, rotated)
        slug = rotated.get("slug")
        mcp_password = rotated.get("password")
        expires = rotated.get("expires_at")
        url = rotated.get("url")
        if not isinstance(slug, str) or not isinstance(mcp_password, str):
            seed_fail("rotate_body", rstatus, rotated)
        # Real apps/api AgentAccessSecretOut has no expires_at; mint ≥24h for the store.
        if not isinstance(expires, str) or not expires.strip():
            from datetime import datetime, timedelta, timezone

            expires = (datetime.now(timezone.utc) + timedelta(hours=36)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
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
        seed_fail("mcp_missing", 0, {})
    if not isinstance(mcp.get("password"), str) or len(mcp["password"]) < 8:
        seed_fail("mcp_password", 0, {})
    if not isinstance(mcp.get("expires_at"), str) or not mcp["expires_at"]:
        seed_fail("mcp_expires", 0, {})
    if not isinstance(mcp.get("slug"), str) or not mcp["slug"]:
        seed_fail("mcp_slug", 0, {})
    if not mcp_initialize_ok(base, str(mcp["slug"]), str(mcp["password"])):
        seed_fail("mcp_initialize", 0, {"code": "agent_bad_credentials"})

    preview = os.environ.get("PLAYWRIGHT_BASE_URL", "").strip()
    if preview and out:
        draft["preview_url"] = preview
        draft["sim_base_url"] = base
        draft["mock_backend_steps"] = [
            "Preview hosts apps/api (KOI_PREVIEW_MOCK=1, SimulatedPaymentProvider, preview DB).",
            "export KOI_SIM_BASE_URL=<preview origin>",
            "export KOI_ALLOW_PREVIEW_SEED=1",
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
