from __future__ import annotations

import json
from typing import Any

import typer
from typer.core import TyperGroup

from koicloud_cli.commands import (
    OUTPUT_OPTION,
    OutputFormat,
    emit_json,
    exit_for_error,
    get_authenticated_client,
)
from koicloud_cli.errors import ApiError, NotLoggedInError

_RUN = "__run__"


class ConfirmGroup(TyperGroup):
    """`confirm <token>` falls through when the first arg is not a subcommand."""

    def resolve_command(self, ctx: Any, args: list[str]) -> tuple[Any, ...]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = [_RUN, *args]
        return super().resolve_command(ctx, args)


app = typer.Typer(
    help="Confirmá o descartá una acción pendiente.",
    cls=ConfirmGroup,
    no_args_is_help=True,
)


@app.command(name=_RUN, hidden=True)
def confirm_token(
    token: str,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Confirma una acción pendiente. Ticket W4-05."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.confirm(token)
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    emit_confirm_result(payload, output=output)


@app.command("cancel")
def cancel_confirmation(
    token: str,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Descarta una acción pendiente. Ticket W4-05."""

    client = None
    try:
        client = get_authenticated_client()
        client.discard_confirmation(token)
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    if output == OutputFormat.JSON:
        emit_json({"ok": True, "token": token})
        return

    typer.echo("Confirmación descartada.")


def emit_confirm_result(payload: Any, *, output: OutputFormat) -> None:
    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    if isinstance(payload, dict):
        summary = payload.get("summary")
        if isinstance(summary, str) and summary:
            typer.echo(summary)
            return
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=True))
        return

    if payload is None:
        typer.echo("Confirmación ejecutada.")
        return

    typer.echo(str(payload))
