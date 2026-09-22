from __future__ import annotations

from typing import Any

import typer

from koicloud_cli.commands import (
    OUTPUT_OPTION,
    YES_TOKEN_OPTION,
    OutputFormat,
    emit_json,
    emit_table,
    exit_for_error,
    exit_unimplemented,
    get_authenticated_client,
)
from koicloud_cli.errors import ApiError, NotLoggedInError

app = typer.Typer(help="Administrá tus ponds.")


@app.command("list")
def list_ponds(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Lista los ponds del usuario."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.request("GET", "ponds")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    ponds = normalize_ponds(payload)
    if output == OutputFormat.JSON:
        emit_json(ponds)
        return

    emit_table(
        ponds,
        title="Ponds",
        columns=[
            ("id", "ID"),
            ("name", "Nombre"),
            ("desired_state", "Deseado"),
            ("observed_state", "Observado"),
            ("engine_version", "Postgres"),
        ],
    )


@app.command("get")
def get_pond(name: str, output: OutputFormat = OUTPUT_OPTION) -> None:
    """Muestra el detalle de un pond. Ticket W4-02."""

    _ = (name, output)
    exit_unimplemented("W4-02", "pond get <name>")


@app.command("create")
def create_pond(
    name: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Crea un pond nuevo. Ticket W4-02."""

    _ = (name, yes, output)
    exit_unimplemented("W4-02", "pond create <name> [--yes TOKEN]")


@app.command("connection")
def pond_connection(name: str, output: OutputFormat = OUTPUT_OPTION) -> None:
    """Muestra la cadena de conexión. Ticket W4-02."""

    _ = (name, output)
    exit_unimplemented("W4-02", "pond connection <name>")


@app.command("delete")
def delete_pond(
    name: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Elimina un pond. Ticket W4-02."""

    _ = (name, yes, output)
    exit_unimplemented("W4-02", "pond delete <name> [--yes TOKEN]")


def normalize_ponds(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [row for row in items if isinstance(row, dict)]
    return []
