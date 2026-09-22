from __future__ import annotations

import os

import pytest

from agent.client import ClaimedJob
from agent.drivers.mock_driver import MockDriver
from agent.main import run_once


class FakeClient:
    def __init__(self, job: ClaimedJob) -> None:
        self.job = job
        self.completed = []

    def claim_job(self) -> ClaimedJob | None:
        job, self.job = self.job, None
        return job

    def complete_job(self, job_id, report) -> None:
        self.completed.append((job_id, report))


def test_run_once_reports_mock_fail_next(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_FAIL_NEXT", "create_pond")
    client = FakeClient(
        ClaimedJob.model_validate(
            {
                "id": "job_fail",
                "type": "create_pond",
                "pond_id": "pond_fail",
                "payload": {
                    "name": "pond-fail",
                    "host_port": 15433,
                    "memory_mb": 512,
                    "cpus": 0.5,
                    "db_password_plain": "secret",
                },
            }
        )
    )

    did_work = run_once(client, MockDriver())

    assert did_work is True
    assert client.completed[0][0] == "job_fail"
    assert client.completed[0][1].status == "failed"
    assert client.completed[0][1].error == "MOCK_FAIL_NEXT=create_pond"
    assert "MOCK_FAIL_NEXT" not in os.environ
