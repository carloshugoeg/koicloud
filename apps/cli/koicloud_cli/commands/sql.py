from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from koicloud_cli.client import ApiClient
from koicloud_cli.commands import (
    OUTPUT_OPTION,
    YES_TOKEN_OPTION,
    OutputFormat,
    emit_json,
    emit_table,
    exit_for_error,
    get_authenticated_client,
    render_cell,
)
from koicloud_cli.errors import ApiError, NotLoggedInError

HISTORY_QUERY_MAX_CHARS = 4000

app = typer.Typer(help="Ejecutá SQL contra un pond.")


@app.command("run")
def run_sql(
    pond: str = typer.Option(..., "--pond", help="Nombre del pond."),
    query: str = typer.Option(..., "-q", "--query", help="Consulta SQL."),
    write: bool = typer.Option(False, "--write", help="Activa el modo write."),
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Ejecuta SQL read o write. Ticket W4-03."""

    client = None
    try:
        client = get_authenticated_client()
        if write:
            if yes is not None:
                payload = client.resolve_mutation(
                    "POST",
                    "ponds/_/sql",
                    yes_token=yes,
                )
            else:
                pond_id = resolve_pond_id(client, pond)
                payload = client.resolve_mutation(
                    "POST",
                    f"ponds/{pond_id}/sql",
                    payload={"query": query, "mode": "write"},
                )
        else:
            pond_id = resolve_pond_id(client, pond)
            payload = client.request(
                "POST",
                f"ponds/{pond_id}/sql",
                json={"query": query, "mode": "read"},
            )
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    emit_run_result(payload, output=output)


@app.command("history")
def sql_history(
    pond: str = typer.Option(..., "--pond", help="Nombre del pond."),
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Lista el historial SQL. Ticket W4-03."""

    client = None
    try:
        client = get_authenticated_client()
        pond_id = resolve_pond_id(client, pond)
        payload = client.request("GET", f"ponds/{pond_id}/sql/history")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    emit_history_result(payload, output=output)


def resolve_pond_id(client: ApiClient, name: str) -> str:
    payload = client.request("GET", f"ponds/by-name/{name}")
    pond = extract_pond(payload)
    pond_id = pond.get("id")
    if not pond_id:
        raise ApiError(status_code=404, message="Pond sin id.", code="pond_not_found")
    return str(pond_id)


def extract_pond(payload: object) -> dict[str, object]:
    if isinstance(payload, dict):
        pond = payload.get("pond")
        if isinstance(pond, dict):
            return pond
        if "id" in payload and "name" in payload:
            return payload
    return {}


def is_confirmation(payload: object) -> bool:
    return isinstance(payload, dict) and (
        payload.get("status") == "confirmation_required"
        or payload.get("code") == "confirmation_required"
    )


def emit_run_result(payload: object, *, output: OutputFormat) -> None:
    if is_confirmation(payload):
        assert isinstance(payload, dict)
        emit_confirmation(payload, output=output)
        return

    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    if not isinstance(payload, dict):
        typer.echo(str(payload))
        return

    columns = payload.get("columns")
    rows = payload.get("rows")
    if isinstance(columns, list) and isinstance(rows, list):
        table = Table(title="Resultado SQL")
        labels = [str(col) for col in columns]
        if not labels:
            table.add_column("(sin columnas)")
            for _ in rows:
                table.add_row("—")
        else:
            for label in labels:
                table.add_column(label)
            for row in rows:
                cells = list(row) if isinstance(row, list) else [row]
                padded = cells + [None] * max(0, len(labels) - len(cells))
                table.add_row(*(render_cell(cell) for cell in padded[: len(labels)]))
        Console().print(table)

    row_count = payload.get("row_count")
    duration_ms = payload.get("duration_ms")
    truncated = payload.get("truncated")
    meta_parts: list[str] = []
    if row_count is not None:
        meta_parts.append(f"filas={row_count}")
    if duration_ms is not None:
        meta_parts.append(f"duración={duration_ms}ms")
    if truncated is not None:
        meta_parts.append(f"truncado={'sí' if truncated else 'no'}")
    if meta_parts:
        typer.echo(" · ".join(meta_parts))


def emit_confirmation(payload: dict[str, object], *, output: OutputFormat) -> None:
    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    typer.echo(str(payload.get("summary") or "Confirmación requerida."))
    typer.echo(f"Token: {payload.get('token')}")
    next_step = payload.get("next") if isinstance(payload.get("next"), dict) else {}
    assert isinstance(next_step, dict)
    cli_example = next_step.get("cli_example")
    if cli_example:
        typer.echo(f"Confirmá con: {cli_example}")


def normalize_history_events(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        events = payload.get("events")
        if isinstance(events, list):
            return [row for row in events if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def history_row(event: dict[str, object]) -> dict[str, object]:
    query = event.get("query_truncated")
    query_text = query if isinstance(query, str) else ""
    truncated = len(query_text) >= HISTORY_QUERY_MAX_CHARS
    return {
        "executed_at": event.get("executed_at"),
        "mode": event.get("mode"),
        "query_truncated": query_text,
        "truncated": "sí" if truncated else "no",
        "row_count": event.get("row_count"),
        "duration_ms": event.get("duration_ms"),
    }


def emit_history_result(payload: object, *, output: OutputFormat) -> None:
    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    rows = [history_row(event) for event in normalize_history_events(payload)]
    emit_table(
        rows,
        title="Historial SQL",
        columns=[
            ("executed_at", "Fecha"),
            ("mode", "Modo"),
            ("query_truncated", "Consulta"),
            ("truncated", "Truncado"),
            ("row_count", "Filas"),
            ("duration_ms", "ms"),
        ],
    )
