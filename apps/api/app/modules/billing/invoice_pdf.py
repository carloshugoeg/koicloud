from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fpdf import FPDF

from app.core.config import get_settings
from app.schemas import InvoiceLineOut, InvoiceOut

IVA_RATE = Decimal("0.12")
ACADEMIC_FOOTER = "Factura simulada - proyecto académico"
_MONEY = Decimal("0.0001")


def split_iva(total_usd: Decimal | float | str, *, rate: Decimal = IVA_RATE) -> tuple[Decimal, Decimal]:
    """Split a total that already includes IVA into (subtotal, iva)."""
    total = Decimal(str(total_usd))
    subtotal = (total / (Decimal("1") + rate)).quantize(_MONEY, rounding=ROUND_HALF_UP)
    iva = (total - subtotal).quantize(_MONEY, rounding=ROUND_HALF_UP)
    return subtotal, iva


def _money(value: Decimal | float | str) -> str:
    return f"{Decimal(str(value)).quantize(_MONEY, rounding=ROUND_HALF_UP):.4f}"


def render_invoice_pdf(
    invoice: InvoiceOut,
    lines: list[InvoiceLineOut] | None = None,
    *,
    invoice_dir: str | Path | None = None,
) -> Path:
    """Write a Helvetica PDF for an already-priced invoice under INVOICE_DIR."""
    target_dir = Path(invoice_dir) if invoice_dir is not None else Path(get_settings().invoice_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / f"{invoice.number}.pdf"

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_compression(False)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, "KoiCloud - Factura", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Codigo: {invoice.number}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Emitida: {invoice.issued_at.isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(120, 8, "Descripcion", border=1)
    pdf.cell(0, 8, "Monto USD", border=1, new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.set_font("Helvetica", size=11)
    for line in lines or []:
        pdf.cell(120, 8, line.description[:60], border=1)
        pdf.cell(0, 8, _money(line.amount_usd), border=1, new_x="LMARGIN", new_y="NEXT", align="R")

    pdf.ln(4)
    pdf.cell(120, 8, "Subtotal", border=0)
    pdf.cell(0, 8, _money(invoice.subtotal_usd), new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.cell(120, 8, "IVA 12 %", border=0)
    pdf.cell(0, 8, _money(invoice.iva_usd), new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(120, 8, "Total", border=0)
    pdf.cell(0, 8, _money(invoice.total_usd), new_x="LMARGIN", new_y="NEXT", align="R")

    pdf.set_y(-30)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 8, ACADEMIC_FOOTER, align="C")

    pdf.output(str(out_path))
    return out_path
