from __future__ import annotations

import json

import httpx

from koicloud_cli.client import ApiClient
from koicloud_cli.main import app


def _patch_client(monkeypatch, handler):
    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )


def test_plan_list_reads_catalog(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/plans"
        return httpx.Response(
            200,
            json={
                "plans": [
                    {
                        "id": "micro",
                        "name": "Micro",
                        "price_monthly_usd": 5.0,
                        "max_ponds": 1,
                        "max_storage_gb": 1,
                        "active": True,
                    }
                ]
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["plan", "list"])
    assert result.exit_code == 0
    assert "micro" in result.output
    assert "Micro" in result.output


def test_subscription_subscribe_proposes_confirmation(
    monkeypatch, runner, write_logged_in_config
) -> None:
    write_logged_in_config()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        assert request.method == "POST"
        assert request.url.path == "/api/v1/subscriptions"
        assert json.loads(request.content.decode()) == {"plan_id": "micro"}
        assert request.headers["x-koi-surface"] == "cli"
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf-sub-abc",
                "summary": "Se contratará el plan micro. Expira en 5 min.",
                "expires_at": "2026-10-18T21:05:00Z",
                "next": {"cli_example": "koicloud confirm conf-sub-abc"},
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["subscription", "subscribe", "micro"])
    assert result.exit_code == 0
    assert calls == ["POST /api/v1/subscriptions"]
    assert "Se contratará el plan micro" in result.output
    assert "Token: conf-sub-abc" in result.output


def test_backup_list_resolves_pond_name(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/ponds/by-name/demo"):
            return httpx.Response(200, json={"pond": {"id": "pond_1", "name": "demo"}})
        assert request.url.path == "/api/v1/ponds/pond_1/backups"
        return httpx.Response(
            200,
            json={
                "backups": [
                    {
                        "id": "bak_1",
                        "kind": "daily",
                        "status": "succeeded",
                        "size_bytes": 100,
                        "created_at": "2026-10-01T00:00:00Z",
                    }
                ]
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["backup", "list", "--pond", "demo"])
    assert result.exit_code == 0
    assert "/api/v1/ponds/by-name/demo" in paths
    assert "/api/v1/ponds/pond_1/backups" in paths
    assert "bak_1" in result.output


def test_backup_restore_proposes_confirmation(
    monkeypatch, runner, write_logged_in_config
) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ponds/by-name/demo"):
            return httpx.Response(200, json={"pond": {"id": "pond_1", "name": "demo"}})
        assert request.method == "POST"
        assert request.url.path == "/api/v1/ponds/pond_1/restore"
        assert json.loads(request.content.decode()) == {"backup_id": "bak_1"}
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf-restore-1",
                "summary": "Se restaurará bak_1 en demo.",
                "next": {"cli_example": "koicloud confirm conf-restore-1"},
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["backup", "restore", "--pond", "demo", "--backup", "bak_1"])
    assert result.exit_code == 0
    assert "Se restaurará bak_1" in result.output
    assert "Token: conf-restore-1" in result.output


def test_agent_show_never_prints_password(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/agent-access"
        return httpx.Response(
            200,
            json={
                "slug": "demo-agent",
                "url": "https://koicloud.local/mcp",
                "enabled": True,
                "rotated_at": "2026-10-01T00:00:00Z",
                "password": "should-not-leak",
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["agent", "show"])
    assert result.exit_code == 0
    assert "demo-agent" in result.output
    assert "https://koicloud.local/mcp" in result.output
    assert "should-not-leak" not in result.output

    result_json = runner.invoke(app, ["agent", "show", "-o", "json"])
    assert result_json.exit_code == 0
    payload = json.loads(result_json.output)
    assert payload["slug"] == "demo-agent"
    assert "password" not in payload or payload.get("password") is None


def test_agent_rotate_proposes_confirmation(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/agent-access/rotate"
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf-rotate-1",
                "summary": "Se rotará la password del gate.",
                "next": {"cli_example": "koicloud confirm conf-rotate-1"},
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["agent", "rotate"])
    assert result.exit_code == 0
    assert "Token: conf-rotate-1" in result.output


def test_agent_rotate_yes_shows_password_once(
    monkeypatch, runner, write_logged_in_config
) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/confirm/conf-rotate-yes"
        return httpx.Response(
            200,
            json={
                "slug": "demo-agent",
                "url": "https://koicloud.local/mcp",
                "password": "one-time-secret",
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["agent", "rotate", "--yes", "conf-rotate-yes"])
    assert result.exit_code == 0
    assert "one-time-secret" in result.output
    assert result.output.count("one-time-secret") == 1


def test_usage_with_month_query(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/usage"
        assert request.url.params.get("month") == "2026-09"
        return httpx.Response(
            200,
            json={
                "month": "2026-09",
                "total_instance_hours": 10.5,
                "total_storage_gb_hours": 2.0,
                "ponds": [
                    {
                        "pond_id": "pond_1",
                        "pond_name": "demo",
                        "instance_hours": 10.5,
                        "storage_gb_hours": 2.0,
                    }
                ],
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["usage", "--month", "2026-09"])
    assert result.exit_code == 0
    assert "2026-09" in result.output
    assert "10.5" in result.output
    assert "demo" in result.output


def test_subscription_list_requires_login(runner) -> None:
    result = runner.invoke(app, ["subscription", "list"])
    assert result.exit_code == 1
    assert "Primero corré `koicloud login`" in result.output
