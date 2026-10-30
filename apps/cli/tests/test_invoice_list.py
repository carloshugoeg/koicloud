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


def test_invoice_list_reads_invoices(monkeypatch, runner, write_logged_in_config) -> None:
    write_logged_in_config()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/invoices"
        return httpx.Response(
            200,
            json={
                "invoices": [
                    {
                        "id": "inv_1",
                        "number": "KC-2026-0001",
                        "status": "paid",
                        "total_usd": 5.0,
                        "issued_at": "2026-10-01T00:00:00Z",
                    }
                ],
                "next_cursor": None,
            },
        )

    _patch_client(monkeypatch, handler)
    result = runner.invoke(app, ["invoice", "list"])
    assert result.exit_code == 0
    assert "KC-2026-0001" in result.output
    assert "paid" in result.output

    result_json = runner.invoke(app, ["invoice", "list", "-o", "json"])
    assert result_json.exit_code == 0
    payload = json.loads(result_json.output)
    assert payload[0]["number"] == "KC-2026-0001"
    assert payload[0]["total_usd"] == 5.0
