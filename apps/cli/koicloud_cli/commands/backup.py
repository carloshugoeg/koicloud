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
    resolve_pond_id,
)
from koicloud_cli.errors import ApiError, NotLoggedInError

app = typer.Typer(help="Respaldos de un pond.")

_BACKUP_COLUMNS = [
    ("id", "ID"),
    ("kind", "Tipo"),
    ("status", "Estado"),
    ("size_bytes", "Bytes"),
    ("created_at", "Creado"),
]
_JOB_COLUMNS = [
    ("id", "ID"),
    ("type", "Tipo"),
    ("status", "Estado"),
]


@app.command("list")
def list_backups(
    pond: str = typer.Option(..., "--pond", help="Nombre del pond."),
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Lista respaldos. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        pond_id = resolve_pond_id(client, pond)
        payload = client.request("GET", f"ponds/{pond_id}/backups")
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    backups = normalize_list(payload, "backups", "items")
    if output == OutputFormat.JSON:
        emit_json(backups)
        return

    emit_table(backups, title=f"Backups {pond}", columns=_BACKUP_COLUMNS)


@app.command("restore")
def restore_backup(
    pond: str = typer.Option(..., "--pond", help="Nombre del pond."),
    backup_id: str = typer.Option(..., "--backup", help="ID del respaldo."),
    yes: str | None = YES_TOKEN_OPTION,
    output: OutputFormat = OUTPUT_OPTION,
) -> None:
    """Restaura un respaldo. Ticket W4-04."""

    client = None
    try:
        client = get_authenticated_client()
        if yes:
            payload = client.resolve_mutation(
                "POST",
                f"ponds/{pond}/restore",
                yes_token=yes,
            )
        else:
            pond_id = resolve_pond_id(client, pond)
            payload = client.resolve_mutation(
                "POST",
                f"ponds/{pond_id}/restore",
                payload={"backup_id": backup_id},
            )
    except (ApiError, NotLoggedInError) as error:
        exit_for_error(error)
    finally:
        if client is not None:
            client.close()

    job = _extract_job(payload)
    emit_mutation_result(
        payload,
        output=output,
        title="Restore encolado",
        rows=[job] if job else None,
        columns=_JOB_COLUMNS,
    )


def _extract_job(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        job = payload.get("job")
        if isinstance(job, dict):
            return job
        if "id" in payload and "type" in payload:
            return payload
    return {}
