from __future__ import annotations

import json

import httpx

from koicloud_cli.client import ApiClient
from koicloud_cli.main import app


def test_pond_list_human_output(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/ponds"
        assert request.headers["authorization"] == "Bearer access-token"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "pond_123",
                    "name": "inventario-demo",
                    "desired_state": "running",
                    "observed_state": "running",
                    "engine_version": "16",
                }
            ],
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["pond", "list"])

    assert result.exit_code == 0
    assert "inventario-demo" in result.output
    assert "running" in result.output


def test_pond_list_json_output(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/ponds"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "pond_456",
                    "name": "koi-reporting",
                    "desired_state": "running",
                    "observed_state": "pending",
                    "engine_version": "16",
                }
            ],
        )

    monkeypatch.setattr(
        "koicloud_cli.commands.create_client",
        lambda: ApiClient(transport=httpx.MockTransport(handler)),
    )

    result = runner.invoke(app, ["pond", "list", "-o", "json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == [
        {
            "id": "pond_456",
            "name": "koi-reporting",
            "desired_state": "running",
            "observed_state": "pending",
            "engine_version": "16",
        }
    ]
