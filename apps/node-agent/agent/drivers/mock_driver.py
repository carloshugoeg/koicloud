from __future__ import annotations

import hashlib
import os
import time
from dataclasses import replace
from typing import Any
from uuid import uuid4

from agent.drivers.base import (
    BackupArtifact,
    PondDriver,
    PondDriverError,
    PondRuntime,
    PondSample,
    PondSpec,
)


class MockFailure(PondDriverError):
    """Raised when MOCK_FAIL_NEXT asks the driver to fail."""

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(f"MOCK_FAIL_NEXT={operation}")


class MockDriver(PondDriver):
    """In-memory pond runtime used in dev and CI."""

    def __init__(self, *, latency_ms: int = 0, default_size_bytes: int = 134_217_728) -> None:
        self.latency_ms = latency_ms
        self.default_size_bytes = default_size_bytes
        self._ponds: dict[str, PondRuntime] = {}
        self._sizes: dict[str, int] = {}
        self._backups: dict[str, list[BackupArtifact]] = {}

    @property
    def ponds(self) -> dict[str, PondRuntime]:
        return dict(self._ponds)

    def create_pond(self, spec: PondSpec) -> PondRuntime:
        self._run("create_pond")
        runtime = PondRuntime(
            pond_id=spec.pond_id,
            name=spec.name,
            container_name=f"koicloud-{spec.name}",
            host_port=spec.host_port,
            state="running",
            image=spec.image,
            memory_mb=spec.memory_mb,
            cpus=spec.cpus,
            connection_uri=(
                f"postgresql://postgres:{spec.db_password_plain}@127.0.0.1:{spec.host_port}/{spec.name}"
            ),
        )
        self._ponds[spec.name] = runtime
        self._sizes[spec.name] = self.default_size_bytes
        self._backups.setdefault(spec.name, [])
        return runtime

    def start(self, pond_name: str) -> PondRuntime:
        self._run("start")
        runtime = self._require_pond(pond_name)
        updated = replace(runtime, state="running")
        self._ponds[pond_name] = updated
        return updated

    def stop(self, pond_name: str) -> PondRuntime:
        self._run("stop")
        runtime = self._require_pond(pond_name)
        updated = replace(runtime, state="stopped")
        self._ponds[pond_name] = updated
        return updated

    def delete(self, pond_name: str) -> dict[str, Any]:
        self._run("delete")
        runtime = self._require_pond(pond_name)
        self._ponds.pop(pond_name, None)
        self._sizes.pop(pond_name, None)
        backups = [artifact.to_dict() for artifact in self._backups.pop(pond_name, [])]
        return {"deleted": True, "pond": runtime.to_dict(), "backups": backups}

    def dump(self, pond_name: str, backup_id: str | None = None) -> BackupArtifact:
        self._run("dump")
        runtime = self._require_pond(pond_name)
        resolved_id = backup_id or f"backup_{uuid4().hex[:8]}"
        path = f"/tmp/mock-backups/{pond_name}-{resolved_id}.sql"
        payload = f"mock-dump:{pond_name}:{resolved_id}".encode()
        artifact = BackupArtifact(
            pond_id=runtime.pond_id,
            backup_id=resolved_id,
            path=path,
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )
        self._backups.setdefault(pond_name, []).append(artifact)
        return artifact

    def restore(self, pond_name: str, backup_id: str) -> dict[str, Any]:
        self._run("restore")
        runtime = self._require_pond(pond_name)
        available = self._backups.get(pond_name, [])
        if not any(artifact.backup_id == backup_id for artifact in available):
            raise PondDriverError(f"backup_not_found:{backup_id}")
        updated = replace(runtime, state="running")
        self._ponds[pond_name] = updated
        return {"restored": True, "pond": updated.to_dict(), "backup_id": backup_id}

    def sample(self) -> list[PondSample]:
        self._run("sample")
        return [
            PondSample(
                pond_id=runtime.pond_id,
                name=name,
                size_bytes=self._sizes.get(name, self.default_size_bytes),
                state=runtime.state,
            )
            for name, runtime in sorted(self._ponds.items())
        ]

    def _require_pond(self, pond_name: str) -> PondRuntime:
        try:
            return self._ponds[pond_name]
        except KeyError as error:
            raise PondDriverError(f"pond_not_found:{pond_name}") from error

    def _run(self, operation: str) -> None:
        fail_next = os.environ.get("MOCK_FAIL_NEXT")
        if fail_next == operation:
            del os.environ["MOCK_FAIL_NEXT"]
            raise MockFailure(operation)
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)
