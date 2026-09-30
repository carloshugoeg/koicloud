from __future__ import annotations

import json
import stat
import sys

import httpx

from koicloud_cli.client import ApiClient
from koicloud_cli.config import get_settings
from koicloud_cli.main import app


def test_login_success(monkeypatch, runner) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/auth/login"
        body = json.loads(request.content.decode("utf-8"))
        assert body == {"email": "carlos@koicloud.dev", "password": "secretpassword"}
        return httpx.Response(
            200,
            json={
                "access_token": "mock-access-token",
                "refresh_token": "mock-refresh-token",
                "user": {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "email": "carlos@koicloud.dev",
                    "full_name": "Carlos Hugo Escobar",
                    "role": "client",
                    "status": "active",
                    "email_verified": True,
                    "created_at": "2026-09-22T20:00:00Z",
                },
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        ["login", "--email", "carlos@koicloud.dev", "--password", "secretpassword"],
    )

    assert result.exit_code == 0
    assert "Sesión iniciada como carlos@koicloud.dev." in result.output

    config_path = get_settings().config_path
    assert config_path.exists()
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["access_token"] == "mock-access-token"
    assert saved["refresh_token"] == "mock-refresh-token"
    assert saved["user"]["email"] == "carlos@koicloud.dev"

    if sys.platform != "win32":
        assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


def test_login_json_output(monkeypatch, runner) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "mock-access-token-json",
                "refresh_token": "mock-refresh-token-json",
                "user": {"email": "carlos@koicloud.dev"},
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        ["login", "--email", "carlos@koicloud.dev", "--password", "secretpassword", "-o", "json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["access_token"] == "mock-access-token-json"


def test_login_invalid_credentials(monkeypatch, runner) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "code": "invalid_credentials",
                "message": "Credenciales inválidas.",
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(
        app,
        ["login", "--email", "wrong@koicloud.dev", "--password", "badpassword"],
    )

    assert result.exit_code == 1
    assert "Credenciales inválidas." in result.output
    assert "invalid_credentials" in result.output


def test_whoami_human_output(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/me"
        assert request.headers["authorization"] == "Bearer access-token"
        return httpx.Response(
            200,
            json={
                "user": {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "email": "carlos@koicloud.dev",
                    "full_name": "Carlos Hugo Escobar",
                    "role": "client",
                    "nit": "0614-220999-101-3",
                    "status": "active",
                    "email_verified": True,
                    "created_at": "2026-09-22T20:00:00Z",
                },
                "subscription": {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "plan_id": "micro",
                    "status": "active",
                },
                "ponds_count": 2,
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["whoami"])

    assert result.exit_code == 0
    assert "carlos@koicloud.dev" in result.output
    assert "Carlos Hugo Escobar" in result.output
    assert "micro" in result.output
    assert "2" in result.output


def test_whoami_json_output(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    payload = {
        "user": {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "carlos@koicloud.dev",
            "full_name": "Carlos Hugo Escobar",
            "role": "client",
            "nit": None,
            "status": "active",
            "email_verified": True,
            "created_at": "2026-09-22T20:00:00Z",
        },
        "subscription": None,
        "ponds_count": 0,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/me"
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["whoami", "-o", "json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_whoami_unauthenticated_fails_with_hint(runner) -> None:
    result = runner.invoke(app, ["whoami"])

    assert result.exit_code == 1
    assert "Primero corré `koicloud login`." in result.output


def test_logout_clears_session(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    config_path = get_settings().config_path
    assert config_path.exists()

    logout_called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal logout_called
        if request.url.path == "/api/v1/auth/logout":
            logout_called = True
            return httpx.Response(204)
        return httpx.Response(404)

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0
    assert "Sesión cerrada." in result.output
    assert logout_called is True
    assert not config_path.exists()
