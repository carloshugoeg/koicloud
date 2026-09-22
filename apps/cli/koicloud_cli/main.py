from __future__ import annotations

import typer

from koicloud_cli.commands import (
    OUTPUT_OPTION,
    OutputFormat,
    agent,
    auth,
    backup,
    confirm,
    exit_unimplemented,
    pond,
    sql,
    subscription,
)

app = typer.Typer(help="CLI de KoiCloud.", no_args_is_help=True)

app.command(name="login")(auth.login)
app.command(name="logout")(auth.logout)
app.command(name="whoami")(auth.whoami)
app.add_typer(pond.app, name="pond")
app.add_typer(sql.app, name="sql")
app.add_typer(subscription.app, name="subscription")
app.add_typer(subscription.plan_app, name="plan")
app.add_typer(backup.app, name="backup")
app.add_typer(agent.app, name="agent")
app.add_typer(confirm.app, name="confirm")


@app.command("usage")
def usage(
    month: str | None = typer.Option(None, "--month", help="Mes con formato YYYY-MM."),
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Muestra el uso mensual. Ticket W4-04."""

    _ = (month, output)
    exit_unimplemented("W4-04", "usage [--month YYYY-MM]")


if __name__ == "__main__":
    app()
