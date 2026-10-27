#!/usr/bin/env python3
"""Verify seeded gate-user can login and call /me on the hosted preview sim."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    creds_path = Path(os.environ.get("KOI_GATE_CREDENTIALS_OUT") or "")
    base = (os.environ.get("KOI_SIM_BASE_URL") or "").rstrip("/")
    if not creds_path.is_file() or not base:
        print("missing KOI_GATE_CREDENTIALS_OUT or KOI_SIM_BASE_URL", file=sys.stderr)
        return 2
    creds = json.loads(creds_path.read_text(encoding="utf-8"))
    user = creds.get("user") if isinstance(creds.get("user"), dict) else None
    if not user or not isinstance(user.get("email"), str) or not isinstance(user.get("password"), str):
        print("credentials missing user", file=sys.stderr)
        return 2
    body = json.dumps({"email": user["email"], "password": user["password"]}).encode()
    req = urllib.request.Request(
        base + "/api/v1/auth/login",
        data=body,
        method="POST",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
            status = resp.status
    except urllib.error.HTTPError as exc:
        print(f"login HTTP {exc.code}", file=sys.stderr)
        return 1
    if status != 200 or not isinstance(payload.get("access_token"), str) or not payload["access_token"]:
        print("login missing access_token", file=sys.stderr)
        return 1
    me_req = urllib.request.Request(
        base + "/api/v1/me",
        headers={
            "authorization": "Bearer " + payload["access_token"],
            "accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(me_req, timeout=30) as resp:
            if resp.status != 200:
                print(f"me HTTP {resp.status}", file=sys.stderr)
                return 1
            resp.read()
    except urllib.error.HTTPError as exc:
        print(f"me HTTP {exc.code}", file=sys.stderr)
        return 1
    print("seed login+me ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
