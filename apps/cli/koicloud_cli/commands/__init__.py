from __future__ import annotations

import json
from enum import Enum
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from koicloud_cli.client import ApiClient
from koicloud_cli.errors import ApiError, NotLoggedInError, render_api_error


class OutputFormat(str, Enum):
    HUMAN = "human"
    JSON = "json"


def create_client() -> ApiClient:
    return ApiClient()


def get_authenticated_client() -> ApiClient:
    client = create_client()
    if not client.is_logged_in:
        client.close()
        raise NotLoggedInError()
    return client


def emit_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=True))


def emit_table(rows: list[dict[str, Any]], *, columns: list[tuple[str, str]], title: str) -> None:
    table = Table(title=title)
    for _, label in columns:
        table.add_column(label)
    for row in rows:
        table.add_row(*(render_cell(row.get(key)) for key, _ in columns))
    Console().print(table)


def render_cell(value: Any) -> str:
    if value is None:
        return "—"
    return str(value)


OUTPUT_OPTION = typer.Option(
    OutputFormat.HUMAN,
    "--output",
    "-o",
    case_sensitive=False,
    help="Formato de salida.",
)
YES_TOKEN_OPTION = typer.Option(None, "--yes", help="Confirma usando un token ya emitido.")


def exit_unimplemented(ticket: str, summary: str, *, requires_auth: bool = True) -> None:
    client: ApiClient | None = None
    try:
        if requires_auth:
            client = get_authenticated_client()
        typer.echo(f"Pendiente ({ticket}): {summary}", err=True)
        raise typer.Exit(1)
    finally:
        if client is not None:
            client.close()


def exit_for_error(error: Exception) -> None:
    if isinstance(error, NotLoggedInError):
        typer.echo(str(error), err=True)
        raise typer.Exit(1)
    if isinstance(error, ApiError):
        typer.echo(render_api_error(error), err=True)
        raise typer.Exit(1)
    raise error


def is_confirmation(payload: Any) -> bool:
    return isinstance(payload, dict) and (
        payload.get("status") == "confirmation_required" or payload.get("code") == "confirmation_required"
    )


def emit_mutation_result(
    payload: Any,
    *,
    output: OutputFormat,
    title: str,
    rows: list[dict[str, Any]] | None = None,
    columns: list[tuple[str, str]] | None = None,
    after: list[str] | None = None,
) -> None:
    if is_confirmation(payload):
        if output == OutputFormat.JSON:
            emit_json(payload)
            return
        typer.echo(str(payload.get("summary") or "Confirmación requerida."))
        typer.echo(f"Token: {payload.get('token')}")
        next_step = payload.get("next") if isinstance(payload.get("next"), dict) else {}
        cli_example = next_step.get("cli_example")
        if cli_example:
            typer.echo(f"Confirmá con: {cli_example}")
        return

    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    if rows and columns:
        emit_table(rows, title=title, columns=columns)
    else:
        typer.echo(title)
    for line in after or []:
        typer.echo(line)


def normalize_list(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in keys:
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def resolve_pond_id(client: ApiClient, name: str) -> str:
    payload = client.request("GET", f"ponds/by-name/{name}")
    pond: dict[str, Any] = {}
    if isinstance(payload, dict):
        nested = payload.get("pond")
        if isinstance(nested, dict):
            pond = nested
        elif "id" in payload:
            pond = payload
    pond_id = pond.get("id")
    if not pond_id:
        raise ApiError(status_code=404, message="Pond sin id.", code="pond_not_found")
    return str(pond_id)
