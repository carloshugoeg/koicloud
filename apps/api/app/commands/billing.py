from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.enums import AppSurface, InvoiceStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import Plan
from app.core.time import utc_now
from app.modules.billing.invoice_pdf import render_invoice_pdf, split_iva
from app.schemas import (
    CancelSubscriptionResponse,
    ConfirmationRequiredResponse,
    InvoiceDetailResponse,
    InvoiceLineOut,
    InvoiceListResponse,
    InvoiceOut,
    OkResponse,
    PaymentOut,
    PlanListResponse,
    PlanOut,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionListResponse,
    SubscriptionOut,
)

MICRO_TOTAL = 5.0
MICRO_CODE = "KC-2026-000001"
# Fixture-backed invoice ownership until G1 persistence (process-local).
_FIXTURE_OWNERS: dict[UUID, UUID] = {}


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


async def list_my_subscriptions(_: AuthContext) -> SubscriptionListResponse:
    return SubscriptionListResponse.example()


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

    subscription = SubscriptionOut.example()
    subscription.user_id = UUID(actor.user_id)
    subscription.plan_id = payload.plan_id

    invoice = InvoiceDetailResponse.example().invoice
    payment = PaymentOut.example()
    return SubscribeResponse(subscription=subscription, invoice=invoice, payment=payment)


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
    subscription = SubscriptionOut.example()
    subscription.id = subscription_id
    subscription.cancel_at_period_end = True
    return CancelSubscriptionResponse(subscription=subscription)


async def list_invoices(_: AuthContext) -> InvoiceListResponse:
    return InvoiceListResponse.example()


def _fixture_invoice_detail(actor: AuthContext, invoice_id: UUID) -> InvoiceDetailResponse:
    """Demo invoice until G1 persistence. First caller claims ownership of the id."""
    owner = _FIXTURE_OWNERS.get(invoice_id)
    actor_id = UUID(actor.user_id)
    if owner is None:
        _FIXTURE_OWNERS[invoice_id] = actor_id
        owner = actor_id
    elif owner != actor_id:
        raise AppError(ErrorCode.NOT_OWNER)

    subtotal, iva = split_iva(MICRO_TOTAL)
    invoice = InvoiceOut(
        id=invoice_id,
        number=MICRO_CODE,
        user_id=owner,
        subscription_id=SubscriptionOut.example().id,
        subtotal_usd=float(subtotal),
        iva_usd=float(iva),
        total_usd=MICRO_TOTAL,
        status=InvoiceStatus.PAID,
        issued_at=utc_now(),
        pdf_path=None,
    )
    lines = [
        InvoiceLineOut(
            id=InvoiceLineOut.example().id,
            invoice_id=invoice_id,
            description="Plan Micro mensual",
            amount_usd=float(subtotal),
        )
    ]
    return InvoiceDetailResponse(invoice=invoice, lines=lines)


async def get_invoice(actor: AuthContext, invoice_id: UUID) -> InvoiceDetailResponse:
    return _fixture_invoice_detail(actor, invoice_id)


async def get_invoice_pdf(actor: AuthContext, invoice_id: UUID) -> bytes:
    detail = await get_invoice(actor, invoice_id)
    path = render_invoice_pdf(
        detail.invoice,
        detail.lines,
        invoice_dir=Path(get_settings().invoice_dir),
    )
    return path.read_bytes()


async def mark_invoice_sent() -> OkResponse:
    return OkResponse(ok=True)
