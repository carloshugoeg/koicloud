from __future__ import annotations

import typer

from koicloud_cli.commands import (
    OUTPUT_OPTION,
    OutputFormat,
    emit_json,
    emit_table,
    exit_for_error,
    get_authenticated_client,
    normalize_list,
)
from koicloud_cli.errors import ApiError, NotLoggedInError

app = typer.Typer(help="Facturas del usuario.")

_INVOICE_COLUMNS = [
    ("number", "Número"),
    ("status", "Estado"),
    ("total_usd", "Total USD"),
    ("issued_at", "Emitida"),
]


@app.command("list")
def list_invoices(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Lista las facturas del usuario."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.request("GET", "invoices")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    invoices = normalize_list(payload, "invoices", "items")
    if output == OutputFormat.JSON:
        emit_json(invoices)
        return

    emit_table(invoices, title="Facturas", columns=_INVOICE_COLUMNS)
