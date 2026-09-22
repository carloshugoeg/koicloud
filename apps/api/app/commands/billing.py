from __future__ import annotations

from uuid import UUID

from app.commands import build_confirmation
from app.core.auth import AuthContext
from app.core.enums import AppSurface
from app.core.errors import AppError, ErrorCode
from app.schemas import (
    CancelSubscriptionResponse,
    ConfirmationRequiredResponse,
    InvoiceDetailResponse,
    InvoiceListResponse,
    OkResponse,
    PaymentOut,
    PlanListResponse,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionListResponse,
    SubscriptionOut,
)


def _requires_confirmation(surface: AppSurface, confirm_token: str | None) -> bool:
    return surface in {AppSurface.CLI, AppSurface.MCP} and not confirm_token


async def list_plans() -> PlanListResponse:
    return PlanListResponse.example()


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
        return build_confirmation(
            action="subscribe",
            summary=f"Se contratará el plan '{payload.plan_id}' para {actor.email}. Expira en 5 min.",
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
        return build_confirmation(
            action="cancel_subscription",
            summary=(
                f"Se cancelará la suscripción '{subscription_id}' al final del período "
                f"de {actor.email}. Expira en 5 min."
            ),
        )
    subscription = SubscriptionOut.example()
    subscription.id = subscription_id
    subscription.cancel_at_period_end = True
    return CancelSubscriptionResponse(subscription=subscription)


async def list_invoices(_: AuthContext) -> InvoiceListResponse:
    return InvoiceListResponse.example()


async def get_invoice(_: AuthContext, invoice_id: UUID) -> InvoiceDetailResponse:
    detail = InvoiceDetailResponse.example()
    detail.invoice.id = invoice_id
    return detail


async def get_invoice_pdf(_: AuthContext, __: UUID) -> bytes:
    return b"%PDF-1.4\n% KoiCloud invoice placeholder\n"


async def mark_invoice_sent() -> OkResponse:
    return OkResponse(ok=True)
