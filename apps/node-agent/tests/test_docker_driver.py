from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from agent.client import ClaimedJob
from agent.drivers.base import PondDriverError, PondSpec
from agent.drivers.docker_driver import DockerDriver, container_name_for
from agent.handlers import dispatch


def build_spec(name: str = "inventario-demo") -> PondSpec:
    return PondSpec(
        pond_id="pond_123",
        name=name,
        host_port=15432,
        memory_mb=512,
        cpus=0.5,
        db_password_plain="super-secret",
    )


class FakeImage:
    tags: ClassVar[list[str]] = ["postgres:16-alpine"]


class FakeContainer:
    def __init__(
        self,
        name: str,
        labels: dict[str, str],
        host_port: int,
        registry: dict[str, FakeContainer],
    ) -> None:
        self.name = name
        self.labels = labels
        self.status = "running"
        self.image = FakeImage()
        self.attrs = {"NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": str(host_port)}]}}}
        self.removed = False
        self.execs: list[list[str]] = []
        self.archives: list[str] = []
        self._registry = registry

    def start(self) -> None:
        self.status = "running"

    def stop(self) -> None:
        self.status = "exited"

    def reload(self) -> None:
        return None

    def remove(self, force: bool = False) -> None:
        _ = force
        self.removed = True
        self._registry.pop(self.name, None)

    def exec_run(self, cmd: list[str]) -> tuple[int, bytes]:
        self.execs.append(cmd)
        if cmd[0] == "pg_isready":
            return 0, b"accepting connections"
        if cmd[0] == "pg_dump":
            return 0, b"-- mock dump\n"
        if cmd[0] == "psql":
            return 0, b"RESTORE"
        return 1, b"unknown"

    def put_archive(self, path: str, data: bytes) -> bool:
        self.archives.append(path)
        _ = data
        return True


class FakeContainers:
    def __init__(self) -> None:
        self.items: dict[str, FakeContainer] = {}

    def run(self, image: str, **kwargs: object) -> FakeContainer:
        _ = image
        name = str(kwargs["name"])
        if name in self.items:
            raise RuntimeError(f"Conflict. The container name {name} is already in use")
        labels = dict(kwargs.get("labels") or {})  # type: ignore[arg-type]
        ports = kwargs.get("ports") or {}
        host_port = 15432
        if isinstance(ports, dict) and ports.get("5432/tcp"):
            host_port = int(ports["5432/tcp"])  # type: ignore[arg-type]
        container = FakeContainer(name, labels, host_port, self.items)
        self.items[name] = container
        return container

    def get(self, name: str) -> FakeContainer:
        try:
            return self.items[name]
        except KeyError as error:
            raise NotFound(name) from error

    def list(self, all: bool = False, filters: dict[str, str] | None = None) -> list[FakeContainer]:
        _ = all
        values = list(self.items.values())
        if not filters:
            return values
        wanted = filters.get("label")
        if wanted == "koicloud.managed=true":
            return [item for item in values if item.labels.get("koicloud.managed") == "true"]
        return values


class NotFound(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"404 Client Error for {name}: Not Found")


class FakeClient:
    def __init__(self) -> None:
        self.containers = FakeContainers()


@pytest.fixture
def driver(tmp_path: Path) -> DockerDriver:
    return DockerDriver(
        client=FakeClient(),
        backup_dir=tmp_path,
        public_host="127.0.0.1",
        ready_timeout_seconds=1.0,
    )


def test_docker_driver_create_start_stop_delete_and_sample(driver: DockerDriver) -> None:
    runtime = driver.create_pond(build_spec())
    assert runtime.container_name == "koicloud-inventario-demo"
    assert runtime.state == "running"
    assert runtime.connection_uri.endswith(":15432/inventario_demo")

    samples = driver.sample()
    assert samples[0].name == "inventario-demo"
    assert samples[0].state == "running"

    stopped = driver.stop("inventario-demo")
    assert stopped.state == "stopped"
    started = driver.start("inventario-demo")
    assert started.state == "running"

    deleted = driver.delete("inventario-demo")
    assert deleted["deleted"] is True
    with pytest.raises(PondDriverError, match="pond_not_found"):
        driver.start("inventario-demo")


def test_docker_driver_dump_and_restore(driver: DockerDriver, tmp_path: Path) -> None:
    driver.create_pond(build_spec())
    artifact = driver.dump("inventario-demo", "backup_ab")
    assert Path(artifact.path).read_bytes().startswith(b"-- mock dump")
    assert artifact.backup_id == "backup_ab"

    result = driver.restore("inventario-demo", "backup_ab")
    assert result["restored"] is True
    assert (tmp_path / "inventario-demo-backup_ab.sql").is_file()

    with pytest.raises(PondDriverError, match="backup_not_found"):
        driver.restore("inventario-demo", "missing")


def test_docker_driver_name_conflict(driver: DockerDriver) -> None:
    driver.create_pond(build_spec())
    with pytest.raises(PondDriverError, match="pond_name_taken"):
        driver.create_pond(build_spec())


def test_handlers_dispatch_through_docker_driver(driver: DockerDriver) -> None:
    create = ClaimedJob.model_validate(
        {
            "id": "job_1",
            "type": "create_pond",
            "pond_id": "pond_123",
            "payload": {
                "name": "inventario-demo",
                "host_port": 15432,
                "memory_mb": 512,
                "cpus": 0.5,
                "db_password_plain": "super-secret",
            },
        }
    )
    assert dispatch(create, driver)["pond"]["name"] == "inventario-demo"
    assert container_name_for("inventario-demo") == "koicloud-inventario-demo"

    stop = ClaimedJob.model_validate(
        {"id": "job_2", "type": "stop_pond", "payload": {"name": "inventario-demo"}}
    )
    assert dispatch(stop, driver)["pond"]["state"] == "stopped"

    start = ClaimedJob.model_validate(
        {"id": "job_3", "type": "start_pond", "payload": {"name": "inventario-demo"}}
    )
    assert dispatch(start, driver)["pond"]["state"] == "running"

    backup = ClaimedJob.model_validate(
        {
            "id": "job_4",
            "type": "backup_pond",
            "payload": {"name": "inventario-demo", "backup_id": "b1"},
        }
    )
    assert dispatch(backup, driver)["backup"]["backup_id"] == "b1"

    restore = ClaimedJob.model_validate(
        {
            "id": "job_5",
            "type": "restore_pond",
            "payload": {"name": "inventario-demo", "backup_id": "b1"},
        }
    )
    assert dispatch(restore, driver)["restored"] is True

    delete = ClaimedJob.model_validate(
        {"id": "job_6", "type": "delete_pond", "payload": {"name": "inventario-demo"}}
    )
    assert dispatch(delete, driver)["deleted"] is True
