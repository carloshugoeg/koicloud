from __future__ import annotations

import os

import pytest

from agent.drivers.base import PondSpec
from agent.drivers.mock_driver import MockDriver, MockFailure


def build_spec(name: str = "inventario-demo") -> PondSpec:
    return PondSpec(
        pond_id="pond_123",
        name=name,
        host_port=15432,
        memory_mb=512,
        cpus=0.5,
        db_password_plain="super-secret",
    )


def test_mock_driver_create_pond_and_sample() -> None:
    driver = MockDriver(default_size_bytes=42)

    runtime = driver.create_pond(build_spec())
    samples = driver.sample()

    assert runtime.name == "inventario-demo"
    assert runtime.state == "running"
    assert runtime.connection_uri.endswith("/inventario-demo")
    assert samples[0].pond_id == "pond_123"
    assert samples[0].size_bytes == 42


def test_mock_fail_next_is_one_shot(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = MockDriver()
    monkeypatch.setenv("MOCK_FAIL_NEXT", "create_pond")

    with pytest.raises(MockFailure, match="MOCK_FAIL_NEXT=create_pond"):
        driver.create_pond(build_spec("fallible-pond"))

    assert "MOCK_FAIL_NEXT" not in os.environ

    runtime = driver.create_pond(build_spec("fallible-pond"))
    assert runtime.name == "fallible-pond"
