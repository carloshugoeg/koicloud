"""Restore must leave the pond as the backup was, or leave it untouched."""

from __future__ import annotations

import copy
import io
import re
import tarfile
from pathlib import Path

from agent.client import ClaimedJob, CompletionReport
from agent.drivers.base import PondSpec
from agent.drivers.docker_driver import DockerDriver, database_name_for
from agent.main import run_once

BACKUP_ROWS = ["1", "2", "3", "4", "5", "6", "7"]
PREVIOUS_ROWS = ["101", "102", "103"]
POND_NAME = "inventario-demo"
DATABASE = database_name_for(POND_NAME)


def build_spec() -> PondSpec:
    return PondSpec(
        pond_id="pond_123",
        name=POND_NAME,
        host_port=15432,
        memory_mb=512,
        cpus=0.5,
        db_password_plain="super-secret",
    )


class Database:
    """One Postgres database. DDL commits or rolls back with the session."""

    def __init__(self) -> None:
        self.schemas: dict[str, dict[str, list[str]]] = {"public": {}}
        self._snapshot: dict[str, dict[str, list[str]]] | None = None
        self.aborted = False

    @property
    def in_transaction(self) -> bool:
        return self._snapshot is not None

    def begin(self) -> str | None:
        if self.in_transaction:
            return None
        self._snapshot = copy.deepcopy(self.schemas)
        self.aborted = False
        return None

    def commit(self) -> str | None:
        if not self.in_transaction:
            return "there is no transaction in progress"
        if self.aborted:
            return "current transaction is aborted"
        self._snapshot = None
        return None

    def rollback(self) -> str | None:
        if not self.in_transaction or self._snapshot is None:
            return "there is no transaction in progress"
        self.schemas = self._snapshot
        self._snapshot = None
        self.aborted = False
        return None

    def close(self) -> None:
        if self.in_transaction:
            self.rollback()


class Cluster:
    def __init__(self) -> None:
        self.databases: dict[str, Database] = {}

    def create_database(self, name: str) -> None:
        self.databases[name] = Database()


class SqlContainer:
    def __init__(self, name: str, labels: dict[str, str], cluster: Cluster) -> None:
        self.name = name
        self.labels = labels
        self.status = "running"
        self.files: dict[str, bytes] = {}
        self._cluster = cluster

    def reload(self) -> None:
        return None

    def exec_run(self, cmd: list[str]) -> tuple[int, bytes]:
        if not cmd:
            return 1, b"empty"
        if cmd[0] == "pg_isready":
            return 0, b"accepting connections"
        if cmd[0] == "pg_dump":
            return self._dump(cmd)
        if cmd[0] == "psql":
            return self._psql(cmd)
        return 1, b"unknown"

    def put_archive(self, path: str, data: bytes) -> bool:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            for member in archive.getmembers():
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                self.files[str(Path(path) / member.name)] = extracted.read()
        return True

    def _dump(self, cmd: list[str]) -> tuple[int, bytes]:
        name = next((part for part in reversed(cmd[1:]) if not part.startswith("-")), "")
        database = self._cluster.databases.get(name)
        if database is None:
            return 1, f"database {name} does not exist".encode()
        # Plain pg_dump has no DROP. CREATE fails on the next restore and COPY appends.
        parts = ["-- PostgreSQL database dump\n", "SET statement_timeout = 0;\n"]
        for table, rows in sorted(database.schemas.get("public", {}).items()):
            parts.append(f"CREATE TABLE public.{table} (\n    id integer\n);\n")
            parts.append(f"COPY public.{table} (id) FROM stdin;\n")
            parts.extend(f"{row}\n" for row in rows)
            parts.append("\\.\n")
        return 0, "".join(parts).encode()

    def _psql(self, cmd: list[str]) -> tuple[int, bytes]:
        database_name, script, on_error_stop, single_transaction = _psql_invocation(cmd, self.files)
        database = self._cluster.databases.get(database_name)
        if database is None:
            return 2, f"database {database_name} does not exist".encode()
        if script is None:
            return 1, b"psql: no script"
        if single_transaction:
            database.begin()
        error = _apply_script(database, script, on_error_stop=on_error_stop)
        if single_transaction and error is None:
            error = database.commit()
        database.close()
        if error is None:
            return 0, b"OK"
        # Without ON_ERROR_STOP, psql exits 0 after a script error.
        if on_error_stop:
            return 3, error.encode()
        return 0, error.encode()


class SqlContainers:
    def __init__(self, cluster: Cluster) -> None:
        self.cluster = cluster
        self.items: dict[str, SqlContainer] = {}

    def run(self, image: str, **kwargs: object) -> SqlContainer:
        _ = image
        name = str(kwargs["name"])
        labels_raw = kwargs.get("labels")
        labels = (
            {str(key): str(value) for key, value in labels_raw.items()}
            if isinstance(labels_raw, dict)
            else {}
        )
        pond = labels.get("koicloud.pond", name.removeprefix("koicloud-"))
        self.cluster.create_database(database_name_for(pond))
        container = SqlContainer(name, labels, self.cluster)
        self.items[name] = container
        return container

    def get(self, name: str) -> SqlContainer:
        try:
            return self.items[name]
        except KeyError as error:
            raise RuntimeError(f"404 Client Error for {name}: Not Found") from error


class SqlClient:
    def __init__(self, cluster: Cluster) -> None:
        self.containers = SqlContainers(cluster)


class JobClient:
    def __init__(self, job: ClaimedJob) -> None:
        self.job: ClaimedJob | None = job
        self.completed: list[tuple[str, CompletionReport]] = []

    def claim_job(self) -> ClaimedJob | None:
        job, self.job = self.job, None
        return job

    def complete_job(self, job_id: str, report: CompletionReport) -> None:
        self.completed.append((job_id, report))


def _psql_invocation(
    cmd: list[str],
    files: dict[str, bytes],
) -> tuple[str, str | None, bool, bool]:
    database = "postgres"
    filename: str | None = None
    inline: str | None = None
    on_error_stop = False
    single_transaction = False
    index = 1
    while index < len(cmd):
        arg = cmd[index]
        if arg in {"-d", "-f", "-c", "-v", "--set"} and index + 1 < len(cmd):
            value = cmd[index + 1]
            if arg == "-d":
                database = value
            elif arg == "-f":
                filename = value
            elif arg == "-c":
                inline = value
            elif value.replace(" ", "").upper() in {"ON_ERROR_STOP=1", "ON_ERROR_STOP=ON"}:
                on_error_stop = True
            index += 2
            continue
        if arg in {"-1", "--single-transaction"}:
            single_transaction = True
        index += 1
    script = inline
    if filename is not None:
        payload = files.get(filename)
        script = payload.decode() if payload is not None else None
    return database, script, on_error_stop, single_transaction


def _apply_script(database: Database, script: str, *, on_error_stop: bool) -> str | None:
    for kind, payload in _commands(script):
        if kind == "error":
            error = payload
        elif database.aborted and not payload.lstrip().upper().startswith("ROLLBACK"):
            error = "current transaction is aborted"
        else:
            error = _execute(database, payload)
        if error is None:
            continue
        if database.in_transaction:
            database.aborted = True
        if on_error_stop:
            return error
    return None


def _commands(script: str) -> list[tuple[str, str]]:
    lines = script.splitlines()
    commands: list[tuple[str, str]] = []
    buffer: list[str] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not buffer and (stripped == "" or stripped.startswith("--")):
            index += 1
            continue
        buffer.append(lines[index])
        statement = "\n".join(buffer).strip()
        if (
            statement.upper().startswith("COPY ")
            and "FROM STDIN" in statement.upper()
            and statement.endswith(";")
        ):
            rows: list[str] = []
            index += 1
            while index < len(lines) and lines[index].strip() != "\\.":
                rows.append(lines[index])
                index += 1
            if index >= len(lines):
                commands.append(("error", "unterminated COPY"))
                return commands
            commands.append(("copy", statement + "\n" + "\n".join(rows)))
            buffer = []
            index += 1
            continue
        if statement.endswith(";"):
            commands.append(("sql", statement))
            buffer = []
        index += 1
    if buffer and "\n".join(buffer).strip():
        commands.append(("error", "unterminated statement"))
    return commands


def _execute(database: Database, statement: str) -> str | None:
    if statement.upper().startswith("COPY "):
        return _copy(database, statement)
    body = statement.strip().rstrip(";").strip()
    head = body.split(None, 1)[0].upper() if body else ""
    if head in {"SET", "GRANT", "COMMENT"}:
        return None
    if head == "BEGIN":
        return database.begin()
    if head == "COMMIT":
        return database.commit()
    if head == "ROLLBACK":
        return database.rollback()
    dropped = re.fullmatch(
        r"DROP\s+SCHEMA\s+(IF\s+EXISTS\s+)?([A-Za-z_][\w]*)(?:\s+CASCADE)?",
        body,
        re.IGNORECASE,
    )
    if dropped is not None:
        if_exists, name = dropped.group(1), dropped.group(2)
        if name not in database.schemas:
            return None if if_exists else f"schema {name} does not exist"
        del database.schemas[name]
        return None
    created = re.fullmatch(
        r"CREATE\s+SCHEMA\s+(IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w]*)(?:\s+AUTHORIZATION\s+\S+)?",
        body,
        re.IGNORECASE,
    )
    if created is not None:
        if_not_exists, name = created.group(1), created.group(2)
        if name in database.schemas:
            return None if if_not_exists else f"schema {name} already exists"
        database.schemas[name] = {}
        return None
    table = re.fullmatch(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\s*\(.*\)",
        body,
        re.IGNORECASE | re.DOTALL,
    )
    if table is not None:
        schema, name = table.group(1), table.group(2)
        if schema not in database.schemas:
            return f"schema {schema} does not exist"
        if name in database.schemas[schema]:
            return f"relation {name} already exists"
        database.schemas[schema][name] = []
        return None
    return f"syntax error at {body}"


def _copy(database: Database, statement: str) -> str | None:
    header, _, data = statement.partition("\n")
    matched = re.match(
        r"COPY\s+([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\s*\([^)]*\)\s+FROM\s+stdin\s*;",
        header.strip(),
        re.IGNORECASE,
    )
    if matched is None:
        return "syntax error at COPY"
    schema, name = matched.group(1), matched.group(2)
    if schema not in database.schemas or name not in database.schemas[schema]:
        return f"relation {name} does not exist"
    rows = [line for line in data.split("\n") if line != ""]
    database.schemas[schema][name].extend(rows)
    return None


def _items(cluster: Cluster) -> list[str]:
    return list(cluster.databases[DATABASE].schemas["public"]["items"])


def _run_restore(driver: DockerDriver, job_id: str, backup_id: str) -> CompletionReport:
    client = JobClient(
        ClaimedJob.model_validate(
            {
                "id": job_id,
                "type": "restore_pond",
                "pond_id": "pond_123",
                "payload": {"name": POND_NAME, "backup_id": backup_id},
            }
        )
    )
    assert run_once(client, driver) is True
    assert len(client.completed) == 1
    return client.completed[0][1]


def _pond(tmp_path: Path) -> tuple[Cluster, DockerDriver]:
    cluster = Cluster()
    driver = DockerDriver(
        client=SqlClient(cluster),
        backup_dir=tmp_path,
        public_host="127.0.0.1",
        ready_timeout_seconds=1.0,
    )
    driver.create_pond(build_spec())
    cluster.databases[DATABASE].schemas["public"]["items"] = list(BACKUP_ROWS)
    return cluster, driver


def test_restore_three_times_leaves_seven_rows(tmp_path: Path) -> None:
    cluster, driver = _pond(tmp_path)
    driver.dump(POND_NAME, "bak7")

    for index in range(3):
        report = _run_restore(driver, f"job_restore_{index}", "bak7")
        assert report.status == "succeeded"
        assert _items(cluster) == BACKUP_ROWS


def test_restore_failure_keeps_previous_rows(tmp_path: Path) -> None:
    cluster, driver = _pond(tmp_path)
    artifact = driver.dump(POND_NAME, "bak7")
    cluster.databases[DATABASE].schemas["public"]["items"] = list(PREVIOUS_ROWS)
    dump = Path(artifact.path)
    dump.write_bytes(dump.read_bytes() + b"\nTHIS IS NOT SQL;\n")

    report = _run_restore(driver, "job_restore_fail", "bak7")

    assert report.status == "failed"
    assert _items(cluster) == PREVIOUS_ROWS
