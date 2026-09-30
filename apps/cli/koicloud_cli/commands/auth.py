from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from koicloud_cli import commands
from koicloud_cli.commands import (
    OUTPUT_OPTION,
    OutputFormat,
    emit_json,
    exit_for_error,
    get_authenticated_client,
    render_cell,
)
from koicloud_cli.config import CliConfig, clear_config, save_config
from koicloud_cli.errors import ApiError, NotLoggedInError

app = typer.Typer(help="Autenticación del usuario.")


@app.command()
def login(
    email: str = typer.Option(..., "--email", help="Correo del usuario."),
    password: str = typer.Option(..., "--password", hide_input=True, help="Contraseña."),
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Inicia sesión y guarda los tokens. Ticket W4-01."""
    client = commands.create_client()
    try:
        payload = client.request(
            "POST",
            "auth/login",
            json={"email": email, "password": password},
            needs_auth=False,
        )
    except ApiError as error:
        exit_for_error(error)
    finally:
        client.close()

    config = CliConfig(
        base_url=client.config.base_url,
        access_token=payload.get("access_token"),
        refresh_token=payload.get("refresh_token"),
        user=payload.get("user"),
    )
    save_config(config)

    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    typer.echo(f"Sesión iniciada como {email}.")


@app.command()
def logout(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Cierra sesión y borra la config local. Ticket W4-01."""
    client = commands.create_client()
    try:
        if client.is_logged_in:
            try:
                client.request("POST", "auth/logout", needs_auth=True)
            except ApiError:
                pass
    finally:
        client.close()

    clear_config()

    if output == OutputFormat.JSON:
        emit_json({"ok": True, "message": "Sesión cerrada."})
        return

    typer.echo("Sesión cerrada.")


@app.command()
def whoami(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Muestra el usuario logueado. Ticket W4-01."""
    client = None
    try:
        client = get_authenticated_client()
        payload = client.request("GET", "me")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    user = payload.get("user") if isinstance(payload, dict) else {}
    if not isinstance(user, dict):
        user = {}

    table = Table(title="Usuario actual")
    table.add_column("Campo", style="bold")
    table.add_column("Valor")
    table.add_row("Email", render_cell(user.get("email")))
    table.add_row("Nombre", render_cell(user.get("full_name")))
    table.add_row("Rol", render_cell(user.get("role")))
    subscription = payload.get("subscription") if isinstance(payload, dict) else None
    plan = subscription.get("plan_id") if isinstance(subscription, dict) else None
    table.add_row("Plan", render_cell(plan))
    table.add_row(
        "Ponds",
        render_cell(payload.get("ponds_count") if isinstance(payload, dict) else None),
    )
    Console().print(table)
