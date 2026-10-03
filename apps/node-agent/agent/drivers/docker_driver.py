from __future__ import annotations

import hashlib
import io
import os
import tarfile
import time
from pathlib import Path
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

MANAGED_LABEL = "koicloud.managed"
POND_LABEL = "koicloud.pond"
POND_ID_LABEL = "koicloud.pond_id"


def container_name_for(pond_name: str) -> str:
    return f"koicloud-{pond_name}"


def database_name_for(pond_name: str) -> str:
    return pond_name.replace("-", "_")


class DockerDriver(PondDriver):
    """Real postgres:16-alpine ponds via the local Docker daemon.

    CI stays on ``AGENT_MODE=mock``. Use this driver on a laptop or VPS that
    has a Docker socket (see ``docs/runbooks/local-pond.md``).
    """

    def __init__(
        self,
        *,
        client: Any | None = None,
        backup_dir: Path | None = None,
        public_host: str | None = None,
        ready_timeout_seconds: float = 30.0,
    ) -> None:
        self._client = client
        self.backup_dir = Path(backup_dir or os.environ.get("BACKUP_DIR", "/tmp/koicloud/backups"))
        self.public_host = public_host or os.environ.get("NODE_PUBLIC_HOST", "127.0.0.1")
        self.ready_timeout_seconds = ready_timeout_seconds

    def _docker_client(self) -> Any:
        if self._client is not None:
            return self._client
        import docker

        self._client = docker.from_env()
        return self._client

    def create_pond(self, spec: PondSpec) -> PondRuntime:
        client = self._docker_client()
        name = container_name_for(spec.name)
        database = database_name_for(spec.name)
        try:
            container = client.containers.run(
                spec.image,
                name=name,
                detach=True,
                environment={
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": spec.db_password_plain,
                    "POSTGRES_DB": database,
                },
                ports={"5432/tcp": spec.host_port},
                mem_limit=f"{spec.memory_mb}m",
                nano_cpus=int(spec.cpus * 1_000_000_000),
                labels={
                    MANAGED_LABEL: "true",
                    POND_LABEL: spec.name,
                    POND_ID_LABEL: spec.pond_id,
                },
                restart_policy={"Name": "unless-stopped"},
            )
        except Exception as error:
            raise self._translate_error(error, spec.name) from error
        self._wait_ready(container)
        runtime = self._runtime_from_spec(spec, state="running")
        return runtime

    def start(self, pond_name: str) -> PondRuntime:
        container = self._container(pond_name)
        try:
            container.start()
            container.reload()
        except Exception as error:
            raise self._translate_error(error, pond_name) from error
        self._wait_ready(container)
        return self._runtime_from_container(container, state="running")

    def stop(self, pond_name: str) -> PondRuntime:
        container = self._container(pond_name)
        try:
            container.stop()
            container.reload()
        except Exception as error:
            raise self._translate_error(error, pond_name) from error
        return self._runtime_from_container(container, state="stopped")

    def delete(self, pond_name: str) -> dict[str, Any]:
        container = self._container(pond_name)
        runtime = self._runtime_from_container(container, state=container.status)
        try:
            container.remove(force=True)
        except Exception as error:
            raise self._translate_error(error, pond_name) from error
        return {"deleted": True, "pond": runtime.to_dict(), "backups": []}

    def dump(self, pond_name: str, backup_id: str | None = None) -> BackupArtifact:
        container = self._container(pond_name)
        runtime = self._runtime_from_container(container)
        backup_id = backup_id or f"backup_{uuid4().hex[:8]}"
        database = database_name_for(pond_name)
        code, output = container.exec_run(
            ["pg_dump", "-U", "postgres", "--no-owner", "--no-acl", database]
        )
        if code != 0:
            raise PondDriverError(f"dump_failed:{pond_name}")
        raw = output if isinstance(output, bytes) else str(output).encode()
        path = self.backup_dir / f"{pond_name}-{backup_id}.sql"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return BackupArtifact(
            pond_id=runtime.pond_id,
            backup_id=backup_id,
            path=str(path),
            size_bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
        )

    def restore(self, pond_name: str, backup_id: str) -> dict[str, Any]:
        container = self._container(pond_name)
        path = self.backup_dir / f"{pond_name}-{backup_id}.sql"
        if not path.is_file():
            raise PondDriverError(f"backup_not_found:{backup_id}")
        self._put_file(container, "/tmp/restore.sql", path.read_bytes())
        database = database_name_for(pond_name)
        code, output = container.exec_run(
            ["psql", "-U", "postgres", "-d", database, "-f", "/tmp/restore.sql"]
        )
        if code != 0:
            detail = output.decode() if isinstance(output, bytes) else str(output)
            raise PondDriverError(f"restore_failed:{pond_name}:{detail}")
        container.reload()
        updated = self._runtime_from_container(container, state="running")
        return {"restored": True, "pond": updated.to_dict(), "backup_id": backup_id}

    def sample(self) -> list[PondSample]:
        containers = self._docker_client().containers.list(
            all=True,
            filters={"label": f"{MANAGED_LABEL}=true"},
        )
        samples: list[PondSample] = []
        for container in containers:
            labels = getattr(container, "labels", None) or {}
            name = labels.get(POND_LABEL, container.name.removeprefix("koicloud-"))
            samples.append(
                PondSample(
                    pond_id=labels.get(POND_ID_LABEL, container.name),
                    name=name,
                    size_bytes=0,
                    state="running" if container.status == "running" else "stopped",
                )
            )
        return sorted(samples, key=lambda item: item.name)

    def _container(self, pond_name: str) -> Any:
        try:
            return self._docker_client().containers.get(container_name_for(pond_name))
        except Exception as error:
            if self._is_not_found(error):
                raise PondDriverError(f"pond_not_found:{pond_name}") from error
            raise self._translate_error(error, pond_name) from error

    def _wait_ready(self, container: Any) -> None:
        deadline = time.monotonic() + self.ready_timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                code, _output = container.exec_run(["pg_isready", "-U", "postgres"])
                if code == 0:
                    return
            except (OSError, RuntimeError) as error:  # pragma: no cover - daemon race
                last_error = error
            time.sleep(0.2)
        raise PondDriverError("pond_not_ready") from last_error

    def _runtime_from_spec(self, spec: PondSpec, *, state: str) -> PondRuntime:
        database = database_name_for(spec.name)
        return PondRuntime(
            pond_id=spec.pond_id,
            name=spec.name,
            container_name=container_name_for(spec.name),
            host_port=spec.host_port,
            state=state,
            image=spec.image,
            memory_mb=spec.memory_mb,
            cpus=spec.cpus,
            connection_uri=(
                f"postgresql://postgres:{spec.db_password_plain}"
                f"@{self.public_host}:{spec.host_port}/{database}"
            ),
        )

    def _runtime_from_container(self, container: Any, state: str | None = None) -> PondRuntime:
        labels = getattr(container, "labels", None) or {}
        name = labels.get(POND_LABEL, container.name.removeprefix("koicloud-"))
        host_port = self._published_port(container)
        image = ""
        if getattr(container, "image", None) is not None:
            tags = getattr(container.image, "tags", None) or []
            image = tags[0] if tags else ""
        image = image or "postgres:16-alpine"
        return PondRuntime(
            pond_id=labels.get(POND_ID_LABEL, container.name),
            name=name,
            container_name=container.name,
            host_port=host_port,
            state=state or container.status,
            image=image,
            memory_mb=0,
            cpus=0.0,
            connection_uri=f"postgresql://postgres@{self.public_host}:{host_port}/{database_name_for(name)}",
        )

    def _published_port(self, container: Any) -> int:
        attrs = getattr(container, "attrs", None) or {}
        ports = attrs.get("NetworkSettings", {}).get("Ports", {})
        bindings = ports.get("5432/tcp") or []
        if bindings:
            return int(bindings[0]["HostPort"])
        return 0

    def _put_file(self, container: Any, dest_path: str, data: bytes) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as archive:
            info = tarfile.TarInfo(name=os.path.basename(dest_path))
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        buf.seek(0)
        container.put_archive(os.path.dirname(dest_path) or "/", buf.getvalue())

    def _translate_error(self, error: Exception, pond_name: str) -> PondDriverError:
        message = str(error).lower()
        if self._is_not_found(error):
            return PondDriverError(f"pond_not_found:{pond_name}")
        if "already in use" in message or "conflict" in message:
            return PondDriverError(f"pond_name_taken:{pond_name}")
        if "no space" in message or "disk" in message:
            return PondDriverError("disk_full")
        return PondDriverError(str(error))

    @staticmethod
    def _is_not_found(error: Exception) -> bool:
        name = type(error).__name__
        return name == "NotFound" or "not found" in str(error).lower()
