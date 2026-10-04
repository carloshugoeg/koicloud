from __future__ import annotations

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface
from app.modules.agent_access.service import AgentAccessService
from app.schemas import (
    AgentAccessOut,
    AgentAccessSecretOut,
    ConfirmationRequiredResponse,
    ToggleAgentAccessRequest,
    ToggleAgentAccessResponse,
)


async def get_agent_access(actor: AuthContext) -> AgentAccessOut:
    async with SessionLocal() as session:
        service = AgentAccessService(session, get_settings())
        out = await service.get_or_create_out(actor)
        await session.commit()
        return out


async def rotate_agent_password(
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> AgentAccessSecretOut | ConfirmationRequiredResponse:
    if surface == AppSurface.CLI and not confirm_token:
        return await build_confirmation(
            actor=actor,
            action="rotate_agent_password",
            summary="Se generará una nueva contraseña del acceso agente. Expira en 5 min.",
            payload={},
        )

    async with SessionLocal() as session:
        secret = await AgentAccessService(session, get_settings()).rotate(actor)
        await session.commit()
        return secret


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

    async with SessionLocal() as session:
        enabled = await AgentAccessService(session, get_settings()).toggle(
            actor, enabled=payload.enabled
        )
        await session.commit()
        return ToggleAgentAccessResponse(enabled=enabled)
