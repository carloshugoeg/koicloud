from __future__ import annotations

import typer

from koicloud_cli.commands import OUTPUT_OPTION, YES_TOKEN_OPTION, OutputFormat, exit_unimplemented

app = typer.Typer(help="Gate mínima del MCP.")


@app.command("show")
def show_agent_access(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Muestra el acceso agente. Ticket W4-04."""

    _ = output
    exit_unimplemented("W4-04", "agent show")


@app.command("rotate")
def rotate_agent_access(
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Rota la password del gate. Ticket W4-04."""

    _ = (yes, output)
    exit_unimplemented("W4-04", "agent rotate [--yes TOKEN]")
