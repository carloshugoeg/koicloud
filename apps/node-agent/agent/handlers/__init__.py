from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent.client import ClaimedJob
from agent.drivers.base import PondDriver

from . import backup_pond, create_pond, delete_pond, restore_pond, start_pond, stop_pond

Handler = Callable[[ClaimedJob, PondDriver], dict[str, Any]]

HANDLERS: dict[str, Handler] = {
    "create_pond": create_pond.handle,
    "delete_pond": delete_pond.handle,
    "start_pond": start_pond.handle,
    "stop_pond": stop_pond.handle,
    "backup_pond": backup_pond.handle,
    "restore_pond": restore_pond.handle,
}


def dispatch(job: ClaimedJob, driver: PondDriver) -> dict[str, Any]:
    try:
        handler = HANDLERS[job.type]
    except KeyError as error:
        raise NotImplementedError(f"Unsupported job type: {job.type}") from error
    return handler(job, driver)
