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

    client = None
    try:
        client = get_authenticated_client()
        payload = client.request("GET", f"ponds/by-name/{name}")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    pond = extract_pond(payload)
    if output == OutputFormat.JSON:
        emit_json(pond)
        return

    emit_table(
        [pond],
        title=f"Pond {name}",
        columns=[
            ("id", "ID"),
            ("name", "Nombre"),
            ("desired_state", "Deseado"),
            ("observed_state", "Observado"),
            ("engine_version", "Postgres"),
            ("host_port", "Puerto"),
            ("healthy", "Saludable"),
        ],
    )


@app.command("create")
def create_pond(
    name: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Crea un pond nuevo. Ticket W4-02."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.resolve_mutation(
            "POST",
            "ponds",
            payload={"name": name},
            yes_token=yes,
        )
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    emit_mutation_result(payload, output=output, title="Pond creado")


@app.command("connection")
def pond_connection(name: str, output: OutputFormat = OUTPUT_OPTION) -> None:
    """Muestra la cadena de conexión. Ticket W4-02."""

    client = None
    try:
        client = get_authenticated_client()
        pond_payload = client.request("GET", f"ponds/by-name/{name}")
        pond = extract_pond(pond_payload)
        pond_id = pond.get("id")
        if not pond_id:
            raise ApiError(status_code=404, message="Pond sin id.", code="pond_not_found")
        payload = client.request("GET", f"ponds/{pond_id}/connection")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    connection = extract_connection(payload)
    if output == OutputFormat.JSON:
        emit_json(connection)
        return

    emit_table(
        [connection],
        title=f"Conexión {name}",
        columns=[
            ("host", "Host"),
            ("port", "Puerto"),
            ("database", "Base"),
            ("username", "Usuario"),
            ("password", "Password"),
            ("uri", "URI"),
        ],
    )
    uri = connection.get("uri")
    if uri:
        typer.echo(uri)


@app.command("delete")
def delete_pond(
    name: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Elimina un pond. Ticket W4-02."""

    client = None
    try:
        client = get_authenticated_client()
        if yes:
            payload = client.resolve_mutation("DELETE", f"ponds/{name}", yes_token=yes)
        else:
            pond_payload = client.request("GET", f"ponds/by-name/{name}")
            pond = extract_pond(pond_payload)
            pond_id = pond.get("id")
            if not pond_id:
                raise ApiError(status_code=404, message="Pond sin id.", code="pond_not_found")
            payload = client.resolve_mutation("DELETE", f"ponds/{pond_id}")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    emit_mutation_result(payload, output=output, title="Pond eliminado")


def normalize_ponds(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("ponds", "items"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def extract_pond(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        pond = payload.get("pond")
        if isinstance(pond, dict):
            return pond
        if "id" in payload and "name" in payload:
            return payload
    return {}


def extract_connection(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        connection = payload.get("connection")
        if isinstance(connection, dict):
            return connection
        if "uri" in payload:
            return payload
    return {}


def is_confirmation(payload: Any) -> bool:
    return isinstance(payload, dict) and (
        payload.get("status") == "confirmation_required" or payload.get("code") == "confirmation_required"
    )


def emit_mutation_result(payload: Any, *, output: OutputFormat, title: str) -> None:
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

    if isinstance(payload, dict):
        pond = extract_pond(payload)
        if pond:
            emit_table(
                [pond],
                title=title,
                columns=[
                    ("id", "ID"),
                    ("name", "Nombre"),
                    ("desired_state", "Deseado"),
                    ("observed_state", "Observado"),
                ],
            )
            return
    typer.echo(title)
