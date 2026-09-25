from __future__ import annotations

import httpx

from agent.client import InternalClient


def test_claim_job_unwraps_control_plane_envelope() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/jobs/claim")
        return httpx.Response(
            200,
            json={
                "job": {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "type": "create_pond",
                    "pond_id": "22222222-2222-2222-2222-222222222222",
                    "payload": {
                        "name": "inventario-demo",
                        "host_port": 15007,
                        "memory_mb": 512,
                        "cpus": 0.5,
                        "db_password_plain": "secret",
                        "image": "postgres:16-alpine",
                    },
                }
            },
        )

    client = InternalClient(
        base_url="http://control-plane/internal/v1",
        node_token="token",
        node_id="node-ci",
        transport=httpx.MockTransport(handler),
    )
    job = client.claim_job()
    assert job is not None
    assert job.type == "create_pond"
    assert job.payload["name"] == "inventario-demo"
    client.close()


def test_claim_job_empty_queue_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client = InternalClient(
        base_url="http://control-plane/internal/v1",
        node_token="token",
        node_id="node-ci",
        transport=httpx.MockTransport(handler),
    )
    assert client.claim_job() is None
    client.close()
