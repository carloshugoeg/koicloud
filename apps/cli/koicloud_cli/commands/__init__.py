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
