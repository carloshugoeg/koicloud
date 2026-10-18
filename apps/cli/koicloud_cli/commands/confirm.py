from __future__ import annotations

import json

import typer
import typer._click as click
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

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if _should_default_to_confirm(args, known=set(self.commands)):
            args = [_RUN, *args]
        return super().resolve_command(ctx, args)


app = typer.Typer(
    help="Confirmá o descartá una acción pendiente.",
    cls=ConfirmGroup,
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
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


def _should_default_to_confirm(args: list[str], *, known: set[str]) -> bool:
    """True when argv is `confirm [options] <token> [options]`, not a real subcommand."""

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in known:
            return False
        if arg in {"-o", "--output"}:
            i += 2
            continue
        if arg.startswith("--output="):
            i += 1
            continue
        if arg.startswith("-") and arg != "-":
            i += 1
            continue
        return True
    return False


def emit_confirm_result(payload: object, *, output: OutputFormat) -> None:
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
