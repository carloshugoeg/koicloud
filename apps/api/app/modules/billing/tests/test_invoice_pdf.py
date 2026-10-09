from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.core.enums import InvoiceStatus
from app.core.time import utc_now
from app.modules.billing.invoice_pdf import ACADEMIC_FOOTER, render_invoice_pdf, split_iva
from app.schemas import InvoiceLineOut, InvoiceOut

MICRO_TOTAL = Decimal("5.0000")
MICRO_SUBTOTAL = Decimal("4.4643")
MICRO_IVA = Decimal("0.5357")
MICRO_CODE = "KC-2026-000001"


def test_split_iva_micro_alignment() -> None:
    subtotal, iva = split_iva(MICRO_TOTAL)
    assert subtotal == MICRO_SUBTOTAL
    assert iva == MICRO_IVA
    assert subtotal + iva == MICRO_TOTAL


def test_render_invoice_pdf_micro_fixture(tmp_path: Path) -> None:
    invoice = InvoiceOut(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        number=MICRO_CODE,
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        subscription_id=UUID("22222222-2222-2222-2222-222222222222"),
        subtotal_usd=float(MICRO_SUBTOTAL),
        iva_usd=float(MICRO_IVA),
        total_usd=float(MICRO_TOTAL),
        status=InvoiceStatus.PAID,
        issued_at=utc_now(),
        pdf_path=None,
    )
    lines = [
        InvoiceLineOut(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            invoice_id=invoice.id,
            description="Plan Micro mensual",
            amount_usd=float(MICRO_SUBTOTAL),
        )
    ]

    path = render_invoice_pdf(invoice, lines, invoice_dir=tmp_path)
    assert path == tmp_path / f"{MICRO_CODE}.pdf"
    assert path.is_file()
    data = path.read_bytes()
    assert len(data) > 1024
    assert data.startswith(b"%PDF")

    text = data.decode("latin-1", errors="ignore")
    assert "12" in text
    assert "IVA" in text
    assert ACADEMIC_FOOTER in text
    assert MICRO_CODE in text
