from __future__ import annotations

from agent.drivers.base import PondDriver


def collect_samples(driver: PondDriver) -> list[dict[str, object]]:
    return [sample.to_dict() for sample in driver.sample()]
