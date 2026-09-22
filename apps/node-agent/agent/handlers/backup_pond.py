from __future__ import annotations

from agent.client import ClaimedJob
from agent.drivers.base import PondDriver


def handle(job: ClaimedJob, driver: PondDriver) -> dict[str, object]:
    _ = (job, driver)
    raise NotImplementedError("backup_pond handler scaffold pending follow-up implementation.")
