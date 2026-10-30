from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.config import Settings
from app.core.enums import InvoiceStatus, PaymentStatus, SubscriptionStatus
from app.core.errors import AppError, ErrorCode
from app.core.models import Invoice, InvoiceLine, Payment, Plan, Subscription, User
from app.core.time import utc_now
from app.modules.billing.checks import CARD_DECLINED, CardInput, nit_error
from app.modules.billing.invoice_pdf import render_invoice_pdf, split_iva
from app.modules.billing.payments.port import PaymentProvider
from app.modules.billing.plan_pricing import plan_display_pricing
from app.schemas import (
    InvoiceDetailResponse,
    InvoiceLineOut,
    InvoiceListResponse,
    InvoiceOut,
    PaymentOut,
    PlanListResponse,
    PlanOut,
    SubscribeResponse,
    SubscriptionListResponse,
    SubscriptionOut,
)


async def latest_invoice_id_by_subscription(
    session: AsyncSession, subscription_ids: Sequence[UUID]
) -> dict[UUID, UUID]:
    if not subscription_ids:
        return {}
    rows = (
        await session.execute(
            select(Invoice.subscription_id, Invoice.id)
            .where(Invoice.subscription_id.in_(list(subscription_ids)))
            .distinct(Invoice.subscription_id)
            .order_by(Invoice.subscription_id, Invoice.issued_at.desc(), Invoice.id.desc())
        )
    ).all()
    return {subscription_id: invoice_id for subscription_id, invoice_id in rows}


def subscription_to_out(
    row: Subscription, *, invoice_id: UUID | None = None
) -> SubscriptionOut:
    return SubscriptionOut(
        id=row.id,
        user_id=row.user_id,
        plan_id=row.plan_id,
        status=row.status,
        current_period_start=row.current_period_start,
        current_period_end=row.current_period_end,
        cancel_at_period_end=row.cancel_at_period_end,
        invoice_id=invoice_id,
    )


def invoice_to_out(row: Invoice, *, nit: str | None = None) -> InvoiceOut:
    return InvoiceOut(
        id=row.id,
        number=row.number,
        user_id=row.user_id,
        subscription_id=row.subscription_id,
        subtotal_usd=float(row.subtotal_usd),
        iva_usd=float(row.iva_usd),
        total_usd=float(row.total_usd),
        status=row.status,
        issued_at=row.issued_at,
        pdf_path=row.pdf_path,
        nit=nit,
    )


def payment_to_out(row: Payment) -> PaymentOut:
    return PaymentOut(
        id=row.id,
        invoice_id=row.invoice_id,
        amount_usd=float(row.amount_usd),
        status=row.status,
        method=row.method,
        processed_at=row.processed_at,
    )


class BillingService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        payment_provider: PaymentProvider,
    ) -> None:
        self.session = session
        self.settings = settings
        self.payment_provider = payment_provider

    async def list_plans(self) -> PlanListResponse:
        rows = (
            await self.session.scalars(
                select(Plan).where(Plan.active.is_(True)).order_by(Plan.id)
            )
        ).all()
        plans: list[PlanOut] = []
        for row in rows:
            billing_model, unit_price, currency = plan_display_pricing(row)
            plans.append(
                PlanOut(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    price_monthly_usd=float(row.price_monthly_usd),
                    billing_model=billing_model,
                    unit_price=unit_price,
                    currency=currency,
                    max_ponds=row.max_ponds,
                    max_storage_gb=row.max_storage_gb,
                    validity_minutes=row.validity_minutes,
                    postpaid=row.postpaid,
                    active=row.active,
                )
            )
        return PlanListResponse(plans=plans, next_cursor=None)

    async def list_subscriptions(self, actor: AuthContext) -> SubscriptionListResponse:
        rows = (
            await self.session.scalars(
                select(Subscription)
                .where(Subscription.user_id == UUID(actor.user_id))
                .order_by(Subscription.current_period_start.desc())
            )
        ).all()
        invoice_ids = await latest_invoice_id_by_subscription(
            self.session, [row.id for row in rows]
        )
        return SubscriptionListResponse(
            subscriptions=[
                subscription_to_out(row, invoice_id=invoice_ids.get(row.id)) for row in rows
            ],
            next_cursor=None,
        )

    async def subscribe(
        self,
        actor: AuthContext,
        plan_id: str,
        *,
        nit: str | None = None,
        card: CardInput | None = None,
    ) -> SubscribeResponse:
        if not plan_id:
            raise AppError(ErrorCode.PLAN_REQUIRED)
        plan = await self.session.get(Plan, plan_id)
        if plan is None or not plan.active:
            raise AppError(ErrorCode.PLAN_REQUIRED)
        if nit_error(nit):
            raise AppError(ErrorCode.NIT_INVALID)

        user_id = UUID(actor.user_id)
        user = await self.session.get(User, user_id)
        if user is None:
            raise AppError(ErrorCode.TOKEN_INVALID)
        if nit is not None:
            user.nit = nit

        now = utc_now()
        period_end = now + timedelta(minutes=plan.validity_minutes)
        existing = (
            await self.session.scalars(
                select(Subscription)
                .where(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
                .order_by(Subscription.current_period_start.desc())
            )
        ).all()
        if existing and card is not None:
            subscription = existing[0]
            for extra in existing[1:]:
                extra.status = SubscriptionStatus.CANCELED
            subscription.plan_id = plan.id
            subscription.status = SubscriptionStatus.PENDING_PAYMENT
            subscription.cancel_at_period_end = False
            subscription.current_period_start = now
            subscription.current_period_end = period_end
        else:
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                status=SubscriptionStatus.PENDING_PAYMENT,
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False,
            )
            self.session.add(subscription)
        await self.session.flush()

        # Plano "open" invoice maps to existing InvoiceStatus.issued (frozen OpenAPI).
        invoice = await self._create_invoice(
            user_id=user_id,
            subscription=subscription,
            plan=plan,
            issued_at=now,
        )
        payment = await self._start_and_maybe_confirm(invoice, card=card)
        await self.session.refresh(subscription)
        await self.session.refresh(invoice)
        await self.session.refresh(payment)
        await self.session.refresh(user)
        return SubscribeResponse(
            subscription=subscription_to_out(subscription, invoice_id=invoice.id),
            invoice=invoice_to_out(invoice, nit=user.nit),
            payment=payment_to_out(payment),
        )

    async def renew(self, subscription: Subscription) -> SubscribeResponse:
        """Create the next invoice and run it through the payment port (G2 hook)."""
        plan = await self.session.get(Plan, subscription.plan_id)
        if plan is None or not plan.active:
            raise AppError(ErrorCode.PLAN_REQUIRED)
        user = await self.session.get(User, subscription.user_id)
        now = utc_now()
        subscription.status = SubscriptionStatus.PENDING_PAYMENT
        await self.session.flush()
        invoice = await self._create_invoice(
            user_id=subscription.user_id,
            subscription=subscription,
            plan=plan,
            issued_at=now,
        )
        payment = await self._start_and_maybe_confirm(invoice)
        await self.session.refresh(subscription)
        await self.session.refresh(invoice)
        await self.session.refresh(payment)
        return SubscribeResponse(
            subscription=subscription_to_out(subscription, invoice_id=invoice.id),
            invoice=invoice_to_out(invoice, nit=user.nit if user else None),
            payment=payment_to_out(payment),
        )

    async def confirm_payment(self, provider_ref: str) -> Payment:
        payment = await self.session.scalar(
            select(Payment).where(Payment.provider_ref == provider_ref)
        )
        if payment is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No existe el pago solicitado",
            )
        if payment.status == PaymentStatus.SUCCEEDED:
            return payment

        invoice = await self.session.get(Invoice, payment.invoice_id)
        if invoice is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No existe la factura solicitada",
            )
        subscription = await self.session.get(Subscription, invoice.subscription_id)
        if subscription is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No existe la suscripción solicitada",
            )
        plan = await self.session.get(Plan, subscription.plan_id)
        if plan is None:
            raise AppError(ErrorCode.PLAN_REQUIRED)

        now = utc_now()
        payment.status = PaymentStatus.SUCCEEDED
        payment.processed_at = now
        invoice.status = InvoiceStatus.PAID
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(minutes=plan.validity_minutes)
        await self.session.flush()
        return payment

    async def cancel_subscription(
        self, actor: AuthContext, subscription_id: UUID
    ) -> SubscriptionOut:
        subscription = await self.session.get(Subscription, subscription_id)
        if subscription is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No existe la suscripción solicitada",
            )
        if subscription.user_id != UUID(actor.user_id):
            raise AppError(ErrorCode.NOT_OWNER)
        subscription.cancel_at_period_end = True
        await self.session.flush()
        invoice_ids = await latest_invoice_id_by_subscription(self.session, [subscription.id])
        return subscription_to_out(
            subscription, invoice_id=invoice_ids.get(subscription.id)
        )

    async def list_invoices(self, actor: AuthContext) -> InvoiceListResponse:
        user_id = UUID(actor.user_id)
        user = await self.session.get(User, user_id)
        rows = (
            await self.session.scalars(
                select(Invoice)
                .where(Invoice.user_id == user_id)
                .order_by(Invoice.issued_at.desc())
            )
        ).all()
        nit = user.nit if user else None
        return InvoiceListResponse(
            invoices=[invoice_to_out(row, nit=nit) for row in rows],
            next_cursor=None,
        )

    async def get_invoice(self, actor: AuthContext, invoice_id: UUID) -> InvoiceDetailResponse:
        invoice = await self.session.get(Invoice, invoice_id)
        if invoice is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No existe la factura solicitada",
            )
        if invoice.user_id != UUID(actor.user_id):
            raise AppError(ErrorCode.NOT_OWNER)
        user = await self.session.get(User, invoice.user_id)
        lines = (
            await self.session.scalars(
                select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)
            )
        ).all()
        return InvoiceDetailResponse(
            invoice=invoice_to_out(invoice, nit=user.nit if user else None),
            lines=[
                InvoiceLineOut(
                    id=line.id,
                    invoice_id=line.invoice_id,
                    description=line.description,
                    amount_usd=float(line.amount_usd),
                )
                for line in lines
            ],
        )

    async def get_invoice_pdf(self, actor: AuthContext, invoice_id: UUID) -> bytes:
        detail = await self.get_invoice(actor, invoice_id)
        path = render_invoice_pdf(
            detail.invoice,
            detail.lines,
            invoice_dir=Path(self.settings.invoice_dir),
        )
        invoice = await self.session.get(Invoice, invoice_id)
        if invoice is not None:
            invoice.pdf_path = str(path)
            await self.session.flush()
        return path.read_bytes()

    async def _start_and_maybe_confirm(
        self, invoice: Invoice, *, card: CardInput | None = None
    ) -> Payment:
        attempt = self.payment_provider.start_payment(invoice, card=card)
        if attempt.status == PaymentStatus.FAILED:
            raise AppError(ErrorCode.PAYMENT_DECLINED, message=CARD_DECLINED)
        payment = Payment(
            invoice_id=invoice.id,
            amount_usd=invoice.total_usd,
            status=PaymentStatus.PENDING,
            method=attempt.provider,
            provider=attempt.provider,
            provider_ref=attempt.provider_ref,
            processed_at=None,
        )
        self.session.add(payment)
        await self.session.flush()

        if attempt.status == PaymentStatus.SUCCEEDED:
            return await self.confirm_payment(attempt.provider_ref)
        return payment

    async def _create_invoice(
        self,
        *,
        user_id: UUID,
        subscription: Subscription,
        plan: Plan,
        issued_at: datetime,
    ) -> Invoice:
        total = Decimal(str(plan.price_monthly_usd))
        subtotal, iva = split_iva(total)
        last_error: IntegrityError | None = None
        for _ in range(5):
            number = await self._next_invoice_number(issued_at.year)
            try:
                async with self.session.begin_nested():
                    invoice = Invoice(
                        number=number,
                        user_id=user_id,
                        subscription_id=subscription.id,
                        subtotal_usd=subtotal,
                        iva_usd=iva,
                        total_usd=total,
                        status=InvoiceStatus.ISSUED,
                        issued_at=issued_at,
                    )
                    self.session.add(invoice)
                    await self.session.flush()
            except IntegrityError as exc:
                last_error = exc
                continue
            line = InvoiceLine(
                invoice_id=invoice.id,
                description=f"Plan {plan.name} mensual",
                amount_usd=subtotal,
            )
            self.session.add(line)
            await self.session.flush()
            return invoice
        raise AppError(
            ErrorCode.INTERNAL_ERROR,
            message="No se pudo asignar un número de factura único",
        ) from last_error

    async def _next_invoice_number(self, year: int) -> str:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"koicloud-invoice-{year}"},
        )
        prefix = f"KC-{year}-"
        last = await self.session.scalar(
            select(func.max(Invoice.number)).where(Invoice.number.like(f"{prefix}%"))
        )
        seq = 1 if last is None else int(str(last).rsplit("-", 1)[-1]) + 1
        return f"{prefix}{seq:06d}"
