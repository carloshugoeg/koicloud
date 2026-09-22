from __future__ import annotations

import typer

from koicloud_cli.commands import OUTPUT_OPTION, YES_TOKEN_OPTION, OutputFormat, exit_unimplemented

app = typer.Typer(help="Respaldos de un pond.")


@app.command("list")
def list_backups(
    pond: str = typer.Option(..., "--pond", help="Nombre del pond."),
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Lista respaldos. Ticket W4-04."""

    _ = (pond, output)
    exit_unimplemented("W4-04", "backup list --pond NAME")


@app.command("restore")
def restore_backup(
    pond: str = typer.Option(..., "--pond", help="Nombre del pond."),
    backup_id: str = typer.Option(..., "--backup", help="ID del respaldo."),
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Restaura un respaldo. Ticket W4-04."""

    _ = (pond, backup_id, yes, output)
    exit_unimplemented("W4-04", "backup restore --pond NAME --backup ID [--yes TOKEN]")
