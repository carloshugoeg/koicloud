from __future__ import annotations

import logging
import time

from koicloud_job_sanitize import log_text

from agent.client import CompletionReport, InternalClient
from agent.config import AgentSettings, get_settings
from agent.drivers.base import PondDriver
from agent.drivers.docker_driver import DockerDriver
from agent.drivers.mock_driver import MockDriver
from agent.handlers import dispatch
from agent.sampler import collect_samples

logger = logging.getLogger(__name__)


def _bare_error(raw: str, job_id: str) -> str:
    head = raw.split(":", 1)[0].strip()
    if head == "dump_failed":
        return f"backup_failed:{job_id}"
    if head.endswith("_failed"):
        return f"{head}:{job_id}"
    # Preserve short driver codes such as MOCK_FAIL_NEXT=create_pond.
    return head or "job_failed"


def build_driver(settings: AgentSettings) -> PondDriver:
    if settings.agent_mode == "mock":
        return MockDriver(
            latency_ms=settings.mock_latency_ms,
            default_size_bytes=settings.mock_default_size_bytes,
        )
    if settings.agent_mode == "docker":
        return DockerDriver(backup_dir=settings.backup_dir)
    raise ValueError(f"Unsupported agent mode: {settings.agent_mode}")


def run_once(
    client: InternalClient,
    driver: PondDriver,
    completions: dict[str, CompletionReport] | None = None,
) -> bool:
    job = client.claim_job()
    if job is None:
        return False

    if completions is not None and job.id in completions:
        client.complete_job(job.id, completions[job.id])
        return True

    try:
        result = dispatch(job, driver)
        report = CompletionReport(status="succeeded", result=result)
    except Exception as error:  # noqa: BLE001  # pragma: no cover - exercised by tests via output state
        raw = str(error)
        bare = _bare_error(raw, job.id)
        logger.error("job %s failed: %s", job.id, log_text(raw))
        report = CompletionReport(status="failed", error=bare)

    client.complete_job(job.id, report)
    if completions is not None:
        completions[job.id] = report
    return True


def run_forever(
    client: InternalClient,
    driver: PondDriver,
    settings: AgentSettings,
) -> None:
    completions: dict[str, CompletionReport] = {}
    next_heartbeat = 0.0

    while True:
        now = time.monotonic()
        if now >= next_heartbeat:
            try:
                client.send_heartbeat(containers=[], samples=collect_samples(driver))
            except Exception:
                logger.exception("heartbeat failed")
            next_heartbeat = now + settings.heartbeat_interval_seconds

        did_work = run_once(client, driver, completions=completions)
        if not did_work:
            time.sleep(settings.poll_interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    client = InternalClient.from_settings(settings)
    try:
        run_forever(client, build_driver(settings), settings)
    finally:
        client.close()


if __name__ == "__main__":
    main()
