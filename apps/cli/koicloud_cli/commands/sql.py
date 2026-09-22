from __future__ import annotations

import typer

from koicloud_cli.commands import OUTPUT_OPTION, YES_TOKEN_OPTION, OutputFormat, exit_unimplemented

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

    _ = (pond, query, write, yes, output)
    exit_unimplemented("W4-03", "sql run --pond NAME -q QUERY [--write] [--yes TOKEN]")


@app.command("history")
def sql_history(
    pond: str = typer.Option(..., "--pond", help="Nombre del pond."),
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Lista el historial SQL. Ticket W4-03."""

    _ = (pond, output)
    exit_unimplemented("W4-03", "sql history --pond NAME")
