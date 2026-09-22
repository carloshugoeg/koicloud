from __future__ import annotations

from typing import Annotated

import typer

from koicloud_cli.commands import OUTPUT_OPTION, OutputFormat, exit_unimplemented

app = typer.Typer(
    help="Confirmá o descartá una acción pendiente.",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def confirm_token(
    ctx: typer.Context,
    token: Annotated[str | None, typer.Argument()] = None,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Confirma una acción pendiente. Ticket W4-05."""

    if ctx.invoked_subcommand is not None:
        return
    _ = (token, output)
    exit_unimplemented("W4-05", "confirm <token>")


@app.command("cancel")
def cancel_confirmation(
    token: str,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Descarta una acción pendiente. Ticket W4-05."""

    _ = (token, output)
    exit_unimplemented("W4-05", "confirm cancel <token>")
