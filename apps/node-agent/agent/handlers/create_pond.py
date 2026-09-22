from __future__ import annotations

from agent.client import ClaimedJob
from agent.drivers.base import PondDriver, PondSpec


def handle(job: ClaimedJob, driver: PondDriver) -> dict[str, object]:
    payload = job.payload
    spec = PondSpec(
        pond_id=job.pond_id or payload["name"],
        name=str(payload["name"]),
        host_port=int(payload["host_port"]),
        memory_mb=int(payload.get("memory_mb", 512)),
        cpus=float(payload.get("cpus", 0.5)),
        db_password_plain=str(payload["db_password_plain"]),
        image=str(payload.get("image", "postgres:16-alpine")),
    )
    runtime = driver.create_pond(spec)
    return {"pond": runtime.to_dict()}
