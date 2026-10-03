from __future__ import annotations

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.enums import AppSurface
from app.schemas import (
    AgentAccessOut,
    AgentAccessSecretOut,
    ConfirmationRequiredResponse,
    ToggleAgentAccessRequest,
    ToggleAgentAccessResponse,
)


async def get_agent_access(_: AuthContext) -> AgentAccessOut:
    settings = get_settings()
    return AgentAccessOut(
        slug=settings.mcp_demo_slug,
        url=f"https://{settings.koicloud_domain}{settings.mcp_prefix}",
        enabled=settings.mcp_enabled,
        rotated_at=AgentAccessOut.example().rotated_at,
    )


async def rotate_agent_password(
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> AgentAccessSecretOut | ConfirmationRequiredResponse:
    settings = get_settings()
    if surface == AppSurface.CLI and not confirm_token:
        return await build_confirmation(
            actor=actor,
            action="rotate_agent_password",
            summary="Se generará una nueva contraseña del acceso agente. Expira en 5 min.",
            payload={},
        )
    return AgentAccessSecretOut(
        slug=settings.mcp_demo_slug,
        url=f"https://{settings.koicloud_domain}{settings.mcp_prefix}",
        password=settings.mcp_demo_password,
    )


async def toggle_agent_access(
    payload: ToggleAgentAccessRequest,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> ToggleAgentAccessResponse | ConfirmationRequiredResponse:
    if surface == AppSurface.CLI and not confirm_token:
        return await build_confirmation(
            actor=actor,
            action="toggle_agent_access",
            summary=(
                f"Se {'activará' if payload.enabled else 'desactivará'} el acceso agente. "
                "Expira en 5 min."
            ),
            payload=payload.model_dump(mode="json"),
        )
    return ToggleAgentAccessResponse(enabled=payload.enabled)
