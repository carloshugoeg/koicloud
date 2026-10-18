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
)
from koicloud_cli.errors import ApiError, NotLoggedInError

app = typer.Typer(help="Gate mínima del MCP.")

_SHOW_COLUMNS = [
    ("slug", "Slug"),
    ("url", "URL"),
    ("enabled", "Activo"),
    ("rotated_at", "Rotado"),
]
_ROTATE_COLUMNS = [
    ("slug", "Slug"),
    ("url", "URL"),
    ("password", "Password"),
]


@app.command("show")
def show_agent_access(output: OutputFormat = OUTPUT_OPTION) -> None:
    """Muestra el acceso agente. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.request("GET", "agent-access")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    access = _extract_access(payload)
    if output == OutputFormat.JSON:
        emit_json(access)
        return

    emit_table([access], title="Acceso agente", columns=_SHOW_COLUMNS)


@app.command("rotate")
def rotate_agent_access(
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Rota la password del gate. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        payload = client.resolve_mutation(
            "POST",
            "agent-access/rotate",
            yes_token=yes,
        )
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    secret = _extract_secret(payload)
    emit_mutation_result(
        payload,
        output=output,
        title="Password rotada",
        rows=[secret] if secret else None,
        columns=_ROTATE_COLUMNS,
    )


def _extract_access(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {
            "slug": payload.get("slug"),
            "url": payload.get("url"),
            "enabled": payload.get("enabled"),
            "rotated_at": payload.get("rotated_at"),
        }
    return {}


def _extract_secret(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {
            "slug": payload.get("slug"),
            "url": payload.get("url"),
            "password": payload.get("password"),
        }
    return {}
