from __future__ import annotations

from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from agent.config import AgentSettings


class ClaimedJob(BaseModel):
    id: str
    type: str
    pond_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CompletionReport(BaseModel):
    status: Literal["succeeded", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = None


class InternalClient:
    """httpx client for /internal/v1 calls."""

    def __init__(
        self,
        *,
        base_url: str,
        node_token: str,
        node_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.node_id = node_id
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            timeout=10.0,
            transport=transport,
            headers={
                "Accept": "application/json",
                "X-Node-Token": node_token,
                "X-Node-Id": node_id,
            },
        )

    @classmethod
    def from_settings(
        cls,
        settings: AgentSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> InternalClient:
        return cls(
            base_url=settings.internal_api_url,
            node_token=settings.node_token,
            node_id=settings.node_id,
            transport=transport,
        )

    def claim_job(self, *, max_types: list[str] | None = None) -> ClaimedJob | None:
        payload: dict[str, Any] = {}
        if max_types:
            payload["max_types"] = max_types
        response = self._client.post("jobs/claim", json=payload or None)
        if response.status_code == 204:
            return None
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and "job" in body:
            body = body["job"]
        return ClaimedJob.model_validate(body)

    def complete_job(self, job_id: str, report: CompletionReport | dict[str, Any]) -> None:
        body = report.model_dump(mode="json", exclude_none=True) if isinstance(report, CompletionReport) else report
        response = self._client.post(f"jobs/{job_id}/complete", json=body)
        response.raise_for_status()

    def send_heartbeat(
        self,
        *,
        containers: list[dict[str, Any]],
        samples: list[dict[str, Any]],
    ) -> None:
        mapped_samples: list[dict[str, Any]] = []
        for sample in samples:
            mapped_samples.append(
                {
                    "pond_name": str(sample.get("pond_name") or sample.get("name") or ""),
                    "size_bytes": int(sample.get("size_bytes") or 0),
                    "container_state": str(
                        sample.get("container_state") or sample.get("state") or "unknown"
                    ),
                }
            )
        response = self._client.post(
            "heartbeat",
            json={"containers": containers, "samples": mapped_samples},
        )
        response.raise_for_status()

    def close(self) -> None:
        self._client.close()
