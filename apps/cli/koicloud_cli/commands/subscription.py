from __future__ import annotations

from typing import Any

import typer

from koicloud_cli.commands import (
    OUTPUT_OPTION,
    YES_TOKEN_OPTION,
    OutputFormat,
    emit_json,
    emit_mutation_result,
    emit_table,
    exit_for_error,
    get_authenticated_client,
    normalize_list,
)
from koicloud_cli.errors import ApiError, NotLoggedInError

app = typer.Typer(help="Suscripciones del usuario.")
plan_app = typer.Typer(help="Catálogo de planes.")

_PLAN_COLUMNS = [
    ("id", "ID"),
    ("name", "Nombre"),
    ("price_monthly_usd", "USD/mes"),
    ("max_ponds", "Ponds"),
    ("max_storage_gb", "GB"),
    ("active", "Activo"),
]
_SUB_COLUMNS = [
    ("id", "ID"),
    ("plan_id", "Plan"),
    ("status", "Estado"),
    ("current_period_end", "Fin período"),
    ("cancel_at_period_end", "Cancela al fin"),
]


@plan_app.command("list")
def list_plans(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Lista los planes disponibles. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.request("GET", "plans")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    plans = normalize_list(payload, "plans", "items")
    if output == OutputFormat.JSON:
        emit_json(plans)
        return

    emit_table(plans, title="Planes", columns=_PLAN_COLUMNS)


@app.command("list")
def list_subscriptions(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Lista las suscripciones del usuario. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.request("GET", "subscriptions")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    subscriptions = normalize_list(payload, "subscriptions", "items")
    if output == OutputFormat.JSON:
        emit_json(subscriptions)
        return

    emit_table(subscriptions, title="Suscripciones", columns=_SUB_COLUMNS)


@app.command("subscribe")
def subscribe(
    plan_id: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Contrata un plan. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.resolve_mutation(
            "POST",
            "subscriptions",
            payload={"plan_id": plan_id},
            yes_token=yes,
        )
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    subscription = _extract_subscription(payload)
    emit_mutation_result(
        payload,
        output=output,
        title="Suscripción creada",
        rows=[subscription] if subscription else None,
        columns=_SUB_COLUMNS,
    )


@app.command("cancel")
def cancel_subscription(
    subscription_id: str,
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Cancela una suscripción. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.resolve_mutation(
            "POST",
            f"subscriptions/{subscription_id}/cancel",
            yes_token=yes,
        )
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    subscription = _extract_subscription(payload)
    emit_mutation_result(
        payload,
        output=output,
        title="Suscripción cancelada",
        rows=[subscription] if subscription else None,
        columns=_SUB_COLUMNS,
    )


def _extract_subscription(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        subscription = payload.get("subscription")
        if isinstance(subscription, dict):
            return subscription
        if "id" in payload and "plan_id" in payload:
            return payload
    return {}
