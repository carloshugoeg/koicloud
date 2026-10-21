#!/usr/bin/env python3
"""Replay the sealed MCP demo for inventario-natural against POST /mcp."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

POND_NAME = "inventario-natural"
READ_SQL = "SELECT now()"
ACTIVE_OBSERVED = frozenset({"pending", "provisioning", "restoring", "deleting"})


class ReplayError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class Settings:
    base_url: str
    slug: str
    password: str
    simulate: bool
    poll_s: float
    wait_s: float


@dataclass(frozen=True)
class Turn:
    human: str
    assistant: str
    tool: str
    arguments: tuple[tuple[str, str], ...]
    confirm: bool


DEMO = (
    Turn(
        human=f"dame un pond nuevo llamado {POND_NAME}",
        assistant=(
            f"Voy a crear el pond {POND_NAME}. "
            "La API pide confirmación antes de crearlo."
        ),
        tool="create_pond",
        arguments=(("name", POND_NAME),),
        confirm=True,
    ),
    Turn(
        human=f"corré {READ_SQL} contra {POND_NAME}",
        assistant="Ejecuto la lectura. El modo read no pide confirmación.",
        tool="run_sql",
        arguments=(
            ("pond_name", POND_NAME),
            ("query", READ_SQL),
            ("mode", "read"),
        ),
        confirm=False,
    ),
    Turn(
        human=f"eliminá {POND_NAME} con backup previo",
        assistant=(
            f"Voy a eliminar el pond {POND_NAME}. "
            "El borrado encola un respaldo pre_delete."
        ),
        tool="delete_pond",
        arguments=(("name", POND_NAME),),
        confirm=True,
    ),
)


def mcp_url(base_url: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/mcp"):
        return trimmed
    return trimmed + "/mcp"


def load_settings(argv: list[str] | None) -> Settings:
    parser = argparse.ArgumentParser(
        description="Replay the sealed MCP demo for inventario-natural against POST /mcp."
    )
    parser.add_argument(
        "--simulate-chat",
        action="store_true",
        help="print the exchange as Tú and Asistente",
    )
    args = parser.parse_args(argv)
    return Settings(
        base_url=_env("KOICLOUD_API_URL", "http://127.0.0.1:8000"),
        slug=_env("KOICLOUD_MCP_SLUG", "demo-agent"),
        password=_env("KOICLOUD_MCP_PASSWORD", "koicloud-demo"),
        simulate=args.simulate_chat,
        poll_s=_float_env("KOICLOUD_REPLAY_POLL_S", "2"),
        wait_s=_float_env("KOICLOUD_REPLAY_WAIT_S", "45"),
    )


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _float_env(name: str, default: str) -> float:
    raw = _env(name, default)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ReplayError(name, f"{name} debe ser un número") from exc
    if value < 0:
        raise ReplayError(name, f"{name} no puede ser negativo")
    return value


class McpClient:
    def __init__(self, settings: Settings) -> None:
        self.url = mcp_url(settings.base_url)
        token = base64.b64encode(f"{settings.slug}:{settings.password}".encode()).decode("ascii")
        self._auth = f"Basic {token}"
        self._id = 0

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": self._auth,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode()
                status = response.status
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise _http_error(exc.code, detail) from exc
        except urllib.error.URLError as exc:
            raise ReplayError("unreachable", f"no pude conectar con {self.url}") from exc
        if status != 200:
            raise _http_error(status, raw)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReplayError("bad_json", "POST /mcp no devolvió JSON") from exc
        if not isinstance(body, dict):
            raise ReplayError("bad_json", "POST /mcp no devolvió un objeto")
        error = body.get("error")
        if error is not None:
            raise ReplayError("jsonrpc", _error_text(error))
        result = body.get("result")
        if not isinstance(result, dict):
            raise ReplayError("bad_result", "el result de /mcp no es un objeto")
        return result


def _http_error(status: int, raw: str) -> ReplayError:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return ReplayError("http_error", f"HTTP {status}")
    if isinstance(body, dict) and isinstance(body.get("code"), str):
        message = body.get("message")
        text = message if isinstance(message, str) and message else body["code"]
        return ReplayError(body["code"], text)
    return ReplayError("http_error", f"HTTP {status}")


def _error_text(error: object) -> str:
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message:
            return message
    return "JSON-RPC error"


def say(settings: Settings, role: str, text: str) -> None:
    if role == "Tú" and not settings.simulate:
        return
    if settings.simulate:
        print(f"{role}: {text}")
        return
    print(text)


def say_tool(name: str, arguments: dict[str, Any]) -> None:
    print(f"tool {name} {json.dumps(arguments, ensure_ascii=False, sort_keys=True)}")


def require_confirmation(payload: dict[str, Any]) -> tuple[str, str]:
    if payload.get("status") != "confirmation_required":
        raise ReplayError("missing_confirmation", "la tool no devolvió confirmation_required")
    token = payload.get("token")
    summary = payload.get("summary")
    if not isinstance(token, str) or token == "":
        raise ReplayError("missing_confirmation", "la respuesta no trae token")
    if not isinstance(summary, str) or summary == "":
        raise ReplayError("missing_confirmation", "la respuesta no trae summary")
    return token, summary


def find_pond(client: McpClient) -> dict[str, Any] | None:
    listed = client.call("list_ponds", {})
    ponds = listed.get("ponds")
    if not isinstance(ponds, list):
        raise ReplayError("bad_list", "list_ponds no devolvió ponds")
    found = None
    for item in ponds:
        if isinstance(item, dict) and item.get("name") == POND_NAME:
            found = item
    return found


def observed_state(pond: dict[str, Any]) -> str:
    state = pond.get("observed_state")
    if not isinstance(state, str) or state == "":
        raise ReplayError("bad_pond", "el pond no trae observed_state")
    return state


def wait_until_quiet(settings: Settings, client: McpClient) -> dict[str, Any] | None:
    deadline = time.monotonic() + settings.wait_s
    told = False
    while True:
        pond = find_pond(client)
        if pond is None or observed_state(pond) not in ACTIVE_OBSERVED:
            return pond
        if not told:
            say(
                settings,
                "Asistente",
                (
                    f"El pond {POND_NAME} está en {observed_state(pond)}. "
                    "Espero a que ese job termine antes de confirmar el borrado."
                ),
            )
            told = True
        if time.monotonic() >= deadline:
            raise ReplayError(
                "pond_busy",
                (
                    f"{POND_NAME} sigue en {observed_state(pond)}. "
                    "Borrar con un job en cola responde pond_busy."
                ),
            )
        time.sleep(settings.poll_s)


def announce(settings: Settings, turn: Turn) -> None:
    say(settings, "Tú", turn.human)
    say(settings, "Asistente", turn.assistant)


def exchange(settings: Settings, client: McpClient, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    say_tool(tool, arguments)
    proposed = client.call(tool, arguments)
    token, summary = require_confirmation(proposed)
    say(settings, "Asistente", summary)
    say(settings, "Tú", "confírmalo")
    confirm_args = {"token": token}
    say_tool("confirm_action", confirm_args)
    result = client.call("confirm_action", confirm_args)
    say(settings, "Asistente", format_confirm(result))
    return result


def format_confirm(data: dict[str, Any]) -> str:
    parts: list[str] = []
    pond = data.get("pond")
    if isinstance(pond, dict) and isinstance(pond.get("name"), str):
        desired = pond.get("desired_state")
        parts.append(f"pond {pond['name']} desired {desired}")
    job = data.get("job")
    if isinstance(job, dict):
        parts.append(f"job {job.get('type')} {job.get('status')}")
    jobs = data.get("jobs")
    if isinstance(jobs, list):
        for item in jobs:
            if isinstance(item, dict):
                parts.append(f"job {item.get('type')} {item.get('status')}")
    if parts:
        return ". ".join(parts) + "."
    return json.dumps(data, ensure_ascii=False)


def format_sql(data: dict[str, Any]) -> str:
    columns = data.get("columns")
    rows = data.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return json.dumps(data, ensure_ascii=False)
    lines = [" | ".join(str(column) for column in columns)]
    for row in rows:
        if isinstance(row, list):
            lines.append(" | ".join(str(cell) for cell in row))
    count = data.get("row_count")
    if isinstance(count, int):
        noun = "fila" if count == 1 else "filas"
        lines.append(f"{count} {noun}")
    return "\n".join(lines)


def play_create(settings: Settings, client: McpClient, turn: Turn) -> None:
    announce(settings, turn)
    arguments = dict(turn.arguments)
    for attempt in range(2):
        try:
            exchange(settings, client, turn.tool, arguments)
            return
        except ReplayError as exc:
            if exc.code != "pond_name_taken" or attempt == 1:
                raise
            say(
                settings,
                "Asistente",
                f"El nombre {POND_NAME} ya existe. Lo borro y vuelvo a proponer la creación.",
            )
            drop_leftover(settings, client, announce_reason=False)


def play_read(settings: Settings, client: McpClient, turn: Turn) -> None:
    announce(settings, turn)
    arguments = dict(turn.arguments)
    say_tool(turn.tool, arguments)
    result = client.call(turn.tool, arguments)
    if result.get("status") == "confirmation_required":
        raise ReplayError(
            "unexpected_confirmation",
            "run_sql en modo read no debe pedir confirmación",
        )
    say(settings, "Asistente", format_sql(result))


def play_delete(settings: Settings, client: McpClient, turn: Turn, *, intro: bool) -> None:
    if intro:
        announce(settings, turn)
    arguments = dict(turn.arguments)
    for attempt in range(2):
        pond = wait_until_quiet(settings, client)
        if pond is None:
            if intro:
                raise ReplayError("pond_not_found", f"{POND_NAME} no está para borrarlo")
            return
        try:
            exchange(settings, client, turn.tool, arguments)
            return
        except ReplayError as exc:
            if exc.code != "pond_busy" or attempt == 1:
                raise
            say(
                settings,
                "Asistente",
                "El borrado respondió pond_busy. Espero y vuelvo a pedir confirmación.",
            )


def drop_leftover(settings: Settings, client: McpClient, *, announce_reason: bool) -> None:
    pond = find_pond(client)
    if pond is None:
        return
    if announce_reason:
        say(
            settings,
            "Asistente",
            (
                f"El pond {POND_NAME} ya existe. "
                "Lo elimino con confirmación antes de repetir el guion."
            ),
        )
    delete = DEMO[2]
    play_delete(settings, client, delete, intro=False)
    if find_pond(client) is not None:
        raise ReplayError("pond_left", f"{POND_NAME} sigue existiendo después de borrarlo")


def run(settings: Settings) -> None:
    client = McpClient(settings)
    drop_leftover(settings, client, announce_reason=True)
    play_create(settings, client, DEMO[0])
    play_read(settings, client, DEMO[1])
    play_delete(settings, client, DEMO[2], intro=True)
    if find_pond(client) is not None:
        raise ReplayError("pond_left", f"{POND_NAME} sigue existiendo al final del guion")


def main(argv: list[str] | None = None) -> int:
    try:
        run(load_settings(argv))
    except ReplayError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
