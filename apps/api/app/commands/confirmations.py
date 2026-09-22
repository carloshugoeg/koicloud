from __future__ import annotations

from typing import Any

from app.core.errors import AppError, ErrorCode
from app.schemas import (
    AgentAccessSecretOut,
    CancelSubscriptionResponse,
    CreatePondResponse,
    DeletePondResponse,
    JobResponse,
    SQLResultResponse,
    SubscribeResponse,
    ToggleAgentAccessResponse,
    TriggerBackupResponse,
)


async def confirm_action(token: str) -> dict[str, Any]:
    if not token.startswith("conf-"):
        raise AppError(ErrorCode.CONFIRMATION_NOT_FOUND)

    action_map = {
        "create-pond": CreatePondResponse.example(),
        "delete-pond": DeletePondResponse.example(),
        "subscribe": SubscribeResponse.example(),
        "cancel-subscription": CancelSubscriptionResponse.example(),
        "trigger-backup": TriggerBackupResponse.example(),
        "restore-backup": JobResponse.example(),
        "run-sql-write": SQLResultResponse.example(),
        "rotate-agent-password": AgentAccessSecretOut.example(),
        "toggle-agent-access": ToggleAgentAccessResponse.example(),
        "retry-failed-job": JobResponse.example(),
    }

    for action_slug, payload in action_map.items():
        if action_slug in token:
            return payload.model_dump(mode="json")

    raise AppError(ErrorCode.CONFIRMATION_ACTION_MISMATCH)


async def discard_pending_confirmation(_: str) -> None:
    return None
