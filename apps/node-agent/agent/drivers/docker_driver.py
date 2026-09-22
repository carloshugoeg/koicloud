from __future__ import annotations

from typing import Any

from agent.drivers.base import BackupArtifact, PondDriver, PondRuntime, PondSample, PondSpec


class DockerDriver(PondDriver):
    """Future real Docker-backed pond driver."""

    def _docker_client(self):
        import docker  # Imported lazily so the mock path works without a daemon.

        return docker.from_env()

    def create_pond(self, spec: PondSpec) -> PondRuntime:
        _ = spec
        raise NotImplementedError("DockerDriver.create_pond is not implemented in the Phase 0 scaffold.")

    def start(self, pond_name: str) -> PondRuntime:
        _ = pond_name
        raise NotImplementedError("DockerDriver.start is not implemented in the Phase 0 scaffold.")

    def stop(self, pond_name: str) -> PondRuntime:
        _ = pond_name
        raise NotImplementedError("DockerDriver.stop is not implemented in the Phase 0 scaffold.")

    def delete(self, pond_name: str) -> dict[str, Any]:
        _ = pond_name
        raise NotImplementedError("DockerDriver.delete is not implemented in the Phase 0 scaffold.")

    def dump(self, pond_name: str, backup_id: str | None = None) -> BackupArtifact:
        _ = (pond_name, backup_id)
        raise NotImplementedError("DockerDriver.dump is not implemented in the Phase 0 scaffold.")

    def restore(self, pond_name: str, backup_id: str) -> dict[str, Any]:
        _ = (pond_name, backup_id)
        raise NotImplementedError("DockerDriver.restore is not implemented in the Phase 0 scaffold.")

    def sample(self) -> list[PondSample]:
        raise NotImplementedError("DockerDriver.sample is not implemented in the Phase 0 scaffold.")
