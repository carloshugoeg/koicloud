from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class PondSpec:
    pond_id: str
    name: str
    host_port: int
    memory_mb: int
    cpus: float
    db_password_plain: str
    image: str = "postgres:16-alpine"


@dataclass(slots=True)
class PondRuntime:
    pond_id: str
    name: str
    container_name: str
    host_port: int
    state: str
    image: str
    memory_mb: int
    cpus: float
    connection_uri: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BackupArtifact:
    pond_id: str
    backup_id: str
    path: str
    size_bytes: int = 0
    sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PondSample:
    pond_id: str
    name: str
    size_bytes: int
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PondDriverError(RuntimeError):
    """Base class for driver failures."""


class PondDriver(ABC):
    @abstractmethod
    def create_pond(self, spec: PondSpec) -> PondRuntime:
        raise NotImplementedError

    @abstractmethod
    def start(self, pond_name: str) -> PondRuntime:
        raise NotImplementedError

    @abstractmethod
    def stop(self, pond_name: str) -> PondRuntime:
        raise NotImplementedError

    @abstractmethod
    def delete(self, pond_name: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def dump(self, pond_name: str, backup_id: str | None = None) -> BackupArtifact:
        raise NotImplementedError

    @abstractmethod
    def restore(self, pond_name: str, backup_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def sample(self) -> list[PondSample]:
        raise NotImplementedError
