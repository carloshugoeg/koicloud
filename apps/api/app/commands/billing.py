from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface
from app.core.errors import AppError, ErrorCode
from app.core.models import Plan
from app.modules.billing.payments import get_payment_provider
from app.modules.billing.service import BillingService
from app.schemas import (
    CancelSubscriptionResponse,
    ConfirmationRequiredResponse,
    InvoiceDetailResponse,
    InvoiceListResponse,
    OkResponse,
    PlanListResponse,
    PlanOut,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionListResponse,
)


def _billing_service(session) -> BillingService:
    settings = get_settings()
    return BillingService(session, settings, get_payment_provider(settings))


def _requires_confirmation(surface: AppSurface, confirm_token: str | None) -> bool:
    return surface in {AppSurface.CLI, AppSurface.MCP} and not confirm_token


def _plan_to_out(plan: Plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        price_monthly_usd=float(plan.price_monthly_usd),
        max_ponds=plan.max_ponds,
        max_storage_gb=plan.max_storage_gb,
        validity_minutes=plan.validity_minutes,
        postpaid=plan.postpaid,
        active=plan.active,
    )


async def list_plans() -> PlanListResponse:
    async with SessionLocal() as session:
        rows = (
            await session.scalars(select(Plan).where(Plan.active.is_(True)).order_by(Plan.id))
        ).all()
        return PlanListResponse(plans=[_plan_to_out(row) for row in rows], next_cursor=None)


async def list_my_subscriptions(actor: AuthContext) -> SubscriptionListResponse:
    async with SessionLocal() as session:
        return await _billing_service(session).list_subscriptions(actor)


async def subscribe(
    payload: SubscribeRequest,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> SubscribeResponse | ConfirmationRequiredResponse:
    if not payload.plan_id:
        raise AppError(ErrorCode.PLAN_REQUIRED)
    if _requires_confirmation(surface, confirm_token):
        return await build_confirmation(
            actor=actor,
            action="subscribe",
            summary=f"Se contratará el plan '{payload.plan_id}' para {actor.email}. Expira en 5 min.",
            payload=payload.model_dump(mode="json"),
        )

    async with SessionLocal() as session:
        result = await _billing_service(session).subscribe(actor, payload.plan_id)
        await session.commit()
        return result


async def cancel_subscription(
    subscription_id: UUID,
    *,
    actor: AuthContext,
    surface: AppSurface,
    confirm_token: str | None = None,
) -> CancelSubscriptionResponse | ConfirmationRequiredResponse:
    if _requires_confirmation(surface, confirm_token):
        return await build_confirmation(
            actor=actor,
            action="cancel_subscription",
            summary=(
                f"Se cancelará la suscripción '{subscription_id}' al final del período "
                f"de {actor.email}. Expira en 5 min."
            ),
            payload={"subscription_id": str(subscription_id)},
        )
    async with SessionLocal() as session:
        subscription = await _billing_service(session).cancel_subscription(
            actor, subscription_id
        )
        await session.commit()
        return CancelSubscriptionResponse(subscription=subscription)


async def list_invoices(actor: AuthContext) -> InvoiceListResponse:
    async with SessionLocal() as session:
        return await _billing_service(session).list_invoices(actor)


async def get_invoice(actor: AuthContext, invoice_id: UUID) -> InvoiceDetailResponse:
    async with SessionLocal() as session:
        return await _billing_service(session).get_invoice(actor, invoice_id)


async def get_invoice_pdf(actor: AuthContext, invoice_id: UUID) -> bytes:
    async with SessionLocal() as session:
        pdf = await _billing_service(session).get_invoice_pdf(actor, invoice_id)
        await session.commit()
        return pdf


async def mark_invoice_sent() -> OkResponse:
    return OkResponse(ok=True)
