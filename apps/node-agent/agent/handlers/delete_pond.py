from __future__ import annotations

from agent.client import ClaimedJob
from agent.drivers.base import PondDriver


def handle(job: ClaimedJob, driver: PondDriver) -> dict[str, object]:
    return driver.delete(str(job.payload["name"]))
