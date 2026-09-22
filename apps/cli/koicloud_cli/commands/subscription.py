from __future__ import annotations

import typer

from koicloud_cli.commands import OUTPUT_OPTION, YES_TOKEN_OPTION, OutputFormat, exit_unimplemented

app = typer.Typer(help="Suscripciones del usuario.")
plan_app = typer.Typer(help="Catálogo de planes.")


@plan_app.command("list")
def list_plans(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Lista los planes disponibles. Ticket W4-04."""

    _ = output
    exit_unimplemented("W4-04", "plan list")


@app.command("list")
def list_subscriptions(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Lista las suscripciones del usuario. Ticket W4-04."""

    _ = output
    exit_unimplemented("W4-04", "subscription list")


@app.command("subscribe")
def subscribe(
    plan_id: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Contrata un plan. Ticket W4-04."""

    _ = (plan_id, yes, output)
    exit_unimplemented("W4-04", "subscription subscribe <plan_id> [--yes TOKEN]")


@app.command("cancel")
def cancel_subscription(
    subscription_id: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Cancela una suscripción. Ticket W4-04."""

    _ = (subscription_id, yes, output)
    exit_unimplemented("W4-04", "subscription cancel <sub_id> [--yes TOKEN]")
