from __future__ import annotations

from agent.client import ClaimedJob
from agent.drivers.base import PondDriver


def handle(job: ClaimedJob, driver: PondDriver) -> dict[str, object]:
    artifact = driver.dump(str(job.payload["name"]), job.payload.get("backup_id"))
    return {"backup": artifact.to_dict()}
