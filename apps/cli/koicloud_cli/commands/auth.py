from __future__ import annotations

import typer

from koicloud_cli.commands import OUTPUT_OPTION, OutputFormat, exit_unimplemented

app = typer.Typer(help="Autenticación del usuario.")


@app.command()
def login(
    email: str = typer.Option(..., "--email", help="Correo del usuario."),
    password: str = typer.Option(..., "--password", hide_input=True, help="Contraseña."),
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Inicia sesión y guarda los tokens. Ticket W4-01."""

    _ = (email, password, output)
    exit_unimplemented("W4-01", "login --email --password", requires_auth=False)


@app.command()
def logout(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Cierra sesión y borra la config local. Ticket W4-01."""

    _ = output
    exit_unimplemented("W4-01", "logout")


@app.command()
def whoami(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Muestra el usuario logueado. Ticket W4-01."""

    _ = output
    exit_unimplemented("W4-01", "whoami")
