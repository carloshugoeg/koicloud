from __future__ import annotations

import httpx

from koicloud_cli.client import ApiClient
from koicloud_cli.config import CliConfig


def test_resolve_mutation_returns_confirmation_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/ponds"
        assert request.headers["x-koi-surface"] == "cli"
        return httpx.Response(
            409,
            json={
                "status": "confirmation_required",
                "token": "conf_123",
                "summary": "Se creará el pond 'inventario-demo'.",
                "expires_at": "2026-09-22T20:05:00Z",
                "next": {"cli_example": "koicloud confirm conf_123"},
            },
        )

    client = ApiClient(
        config=CliConfig(
            base_url="https://koicloud.test/api/v1",
            access_token="access-token",
            refresh_token="refresh-token",
        ),
        transport=httpx.MockTransport(handler),
    )

    payload = client.resolve_mutation("POST", "ponds", payload={"name": "inventario-demo"})

    assert payload["token"] == "conf_123"
    assert payload["next"]["cli_example"] == "koicloud confirm conf_123"
