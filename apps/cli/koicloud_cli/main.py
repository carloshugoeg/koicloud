from __future__ import annotations

import typer

from koicloud_cli.commands import (
    OUTPUT_OPTION,
    OutputFormat,
    agent,
    auth,
    backup,
    confirm,
    emit_json,
    emit_table,
    exit_for_error,
    get_authenticated_client,
    pond,
    sql,
    subscription,
)
from koicloud_cli.errors import ApiError, NotLoggedInError

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

    client = None
    try:
        client = get_authenticated_client()
        path = f"usage?month={month}" if month else "usage"
        payload = client.request("GET", path)
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    if output == OutputFormat.JSON:
        emit_json(payload)
        return

    summary = payload if isinstance(payload, dict) else {}
    emit_table(
        [
            {
                "month": summary.get("month"),
                "total_instance_hours": summary.get("total_instance_hours"),
                "total_storage_gb_hours": summary.get("total_storage_gb_hours"),
            }
        ],
        title="Uso mensual",
        columns=[
            ("month", "Mes"),
            ("total_instance_hours", "Horas instancia"),
            ("total_storage_gb_hours", "GB·h storage"),
        ],
    )
    ponds = summary.get("ponds") if isinstance(summary.get("ponds"), list) else []
    pond_rows = [row for row in ponds if isinstance(row, dict)]
    if pond_rows:
        emit_table(
            pond_rows,
            title="Por pond",
            columns=[
                ("pond_name", "Pond"),
                ("instance_hours", "Horas"),
                ("storage_gb_hours", "GB·h"),
            ],
        )


if __name__ == "__main__":
    app()
