from __future__ import annotations

from agent.client import ClaimedJob, CompletionReport
from agent.drivers.base import PondSpec
from agent.drivers.mock_driver import MockDriver
from agent.main import run_once


def build_job(job_id: str = "job_123") -> ClaimedJob:
    return ClaimedJob.model_validate(
        {
            "id": job_id,
            "type": "create_pond",
            "pond_id": "pond_123",
            "payload": {
                "name": "inventario-demo",
                "host_port": 15432,
                "memory_mb": 512,
                "cpus": 0.5,
                "db_password_plain": "super-secret",
                "image": "postgres:16-alpine",
            },
        }
    )


class FakeClient:
    def __init__(self, job: ClaimedJob | None) -> None:
        self.job = job
        self.completed: list[tuple[str, CompletionReport]] = []

    def claim_job(self) -> ClaimedJob | None:
        job, self.job = self.job, None
        return job

    def complete_job(self, job_id: str, report: CompletionReport) -> None:
        self.completed.append((job_id, report))


class GuardDriver(MockDriver):
    def create_pond(self, spec: PondSpec):  # type: ignore[override]
        raise AssertionError(f"cached completion should skip handler: {spec.name}")


def test_run_once_completes_create_pond_job() -> None:
    client = FakeClient(build_job())
    driver = MockDriver()
    completions: dict[str, CompletionReport] = {}

    did_work = run_once(client, driver, completions=completions)

    assert did_work is True
    assert "inventario-demo" in driver.ponds
    assert client.completed[0][0] == "job_123"
    assert client.completed[0][1].status == "succeeded"
    assert client.completed[0][1].result["pond"]["name"] == "inventario-demo"
    assert completions["job_123"].status == "succeeded"


def test_run_once_reposts_cached_completion_without_rerun() -> None:
    cached = CompletionReport(status="succeeded", result={"pond": {"name": "cached-pond"}})
    client = FakeClient(build_job("job_cached"))
    driver = GuardDriver()

    did_work = run_once(client, driver, completions={"job_cached": cached})

    assert did_work is True
    assert client.completed == [("job_cached", cached)]


def test_run_once_returns_false_when_queue_is_empty() -> None:
    client = FakeClient(None)

    assert run_once(client, MockDriver()) is False
    assert client.completed == []
