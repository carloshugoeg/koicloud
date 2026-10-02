from __future__ import annotations

import json

import httpx

from koicloud_cli.client import ApiClient
from koicloud_cli.main import app


def test_pond_get_by_name(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/ponds/by-name/inventario-demo"
        return httpx.Response(
            200,
            json={
                "pond": {
                    "id": "pond_123",
                    "name": "inventario-demo",
                    "desired_state": "running",
                    "observed_state": "running",
                    "engine_version": "16",
                    "host_port": 15007,
                    "healthy": True,
                }
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["pond", "get", "inventario-demo"])

    assert result.exit_code == 0
    assert "inventario-demo" in result.output
    assert "pond_123" in result.output
    assert "15007" in result.output


def test_pond_create_proposes_without_auto_confirm(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        assert request.method == "POST"
        assert request.url.path == "/api/v1/ponds"
        assert request.headers["x-koi-surface"] == "cli"
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf-create-pond-abc",
                "summary": "Se creará el pond 'nuevo-pond'. Expira en 5 min.",
                "expires_at": "2026-10-02T20:05:00Z",
                "next": {"cli_example": "koicloud confirm conf-create-pond-abc"},
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["pond", "create", "nuevo-pond"])

    assert result.exit_code == 0
    assert calls == ["POST /api/v1/ponds"]
    assert "Se creará el pond 'nuevo-pond'" in result.output
    assert "Token: conf-create-pond-abc" in result.output
    assert "koicloud confirm conf-create-pond-abc" in result.output


def test_pond_create_json_confirmation(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf-create-pond-json",
                "summary": "Se creará el pond 'json-pond'. Expira en 5 min.",
                "expires_at": "2026-10-02T20:05:00Z",
                "next": {"cli_example": "koicloud confirm conf-create-pond-json"},
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["pond", "create", "json-pond", "-o", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["token"] == "conf-create-pond-json"
    assert payload["status"] == "confirmation_required"


def test_pond_delete_proposes_with_backup_summary(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/ponds/by-name/borrar-demo"):
            return httpx.Response(
                200,
                json={"pond": {"id": "pond_del", "name": "borrar-demo", "desired_state": "running", "observed_state": "running"}},
            )
        assert request.method == "DELETE"
        assert request.url.path == "/api/v1/ponds/pond_del"
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf-delete-pond-xyz",
                "summary": (
                    "Se eliminará el pond 'borrar-demo'. "
                    "Se creará un respaldo previo automático. Expira en 5 min."
                ),
                "expires_at": "2026-10-02T20:05:00Z",
                "next": {"cli_example": "koicloud confirm conf-delete-pond-xyz"},
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["pond", "delete", "borrar-demo"])

    assert result.exit_code == 0
    assert "/api/v1/ponds/by-name/borrar-demo" in paths
    assert "/api/v1/ponds/pond_del" in paths
    assert "respaldo previo" in result.output
    assert "Token: conf-delete-pond-xyz" in result.output


def test_pond_connection_prints_uri(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ponds/by-name/conn-demo"):
            return httpx.Response(
                200,
                json={"pond": {"id": "pond_conn", "name": "conn-demo"}},
            )
        assert request.url.path == "/api/v1/ponds/pond_conn/connection"
        return httpx.Response(
            200,
            json={
                "connection": {
                    "host": "db.koicloud.dev",
                    "port": 15007,
                    "database": "conn_demo",
                    "username": "koi_user",
                    "password": "secret",
                    "uri": "postgresql://koi_user:secret@db.koicloud.dev:15007/conn_demo",
                }
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["pond", "connection", "conn-demo"])

    assert result.exit_code == 0
    assert "postgresql://koi_user:secret@db.koicloud.dev:15007/conn_demo" in result.output


def test_pond_get_requires_login(runner) -> None:
    result = runner.invoke(app, ["pond", "get", "x"])
    assert result.exit_code == 1
    assert "Primero corré `koicloud login`" in result.output
