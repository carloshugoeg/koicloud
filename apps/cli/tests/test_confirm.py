from __future__ import annotations

import json

import httpx

from koicloud_cli.client import ApiClient
from koicloud_cli.main import app


def test_confirm_executes_pending_action(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        assert request.headers["x-koi-surface"] == "cli"
        assert request.headers["authorization"] == "Bearer access-token"
        assert request.method == "POST"
        assert request.url.path == "/api/v1/confirm/conf-create-pond-abc"
        return httpx.Response(
            202,
            json={
                "pond": {
                    "id": "pond_123",
                    "name": "nuevo-pond",
                    "desired_state": "running",
                    "observed_state": "creating",
                },
                "summary": "Pond 'nuevo-pond' en cola de creación.",
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["confirm", "conf-create-pond-abc"])

    assert result.exit_code == 0
    assert calls == ["POST /api/v1/confirm/conf-create-pond-abc"]
    assert "Pond 'nuevo-pond' en cola de creación." in result.output


def test_confirm_json_keeps_backend_keys(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    backend = {
        "pond": {
            "id": "pond_json",
            "name": "json-pond",
            "desired_state": "running",
            "observed_state": "creating",
        },
        "job_id": "job_99",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/confirm/conf-json"
        return httpx.Response(202, json=backend)

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["confirm", "conf-json", "-o", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == backend
    assert "job_id" in payload
    assert payload["pond"]["name"] == "json-pond"


def test_confirm_cancel_discards_token(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        assert request.headers["x-koi-surface"] == "cli"
        assert request.method == "DELETE"
        assert request.url.path == "/api/v1/confirm/conf-to-cancel"
        return httpx.Response(204)

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["confirm", "cancel", "conf-to-cancel"])

    assert result.exit_code == 0
    assert calls == ["DELETE /api/v1/confirm/conf-to-cancel"]
    assert "Confirmación descartada." in result.output


def test_confirm_cancel_json(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        return httpx.Response(204)

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["confirm", "cancel", "conf-cancel-json", "-o", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {"ok": True, "token": "conf-cancel-json"}


def test_confirm_not_found(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "code": "confirmation_not_found",
                "message": "No hay una confirmación pendiente con ese token.",
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["confirm", "conf-missing"])

    assert result.exit_code == 1
    assert "confirmation_not_found" in result.output


def test_confirm_expired(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            410,
            json={
                "code": "confirmation_expired",
                "message": "El token de confirmación expiró.",
            },
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["confirm", "conf-expired"])

    assert result.exit_code == 1
    assert "confirmation_expired" in result.output


def test_confirm_logged_out(runner) -> None:
    result = runner.invoke(app, ["confirm", "conf-any"])

    assert result.exit_code == 1
    assert "Primero corré `koicloud login`." in result.output
