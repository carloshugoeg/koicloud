"""Widen invoice money columns for IVA-included Micro totals.

Revision ID: 0003_billing_invoice_money
Revises: 0002_seed_plans
Create Date: 2026-10-09 15:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_billing_invoice_money"
down_revision = "0002_seed_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, columns in (
        ("invoices", ("subtotal_usd", "iva_usd", "total_usd")),
        ("invoice_lines", ("amount_usd",)),
        ("payments", ("amount_usd",)),
    ):
        for column in columns:
            op.alter_column(
                table,
                column,
                existing_type=sa.Numeric(10, 2),
                type_=sa.Numeric(12, 4),
                existing_nullable=False,
            )


def downgrade() -> None:
    for table, columns in (
        ("invoices", ("subtotal_usd", "iva_usd", "total_usd")),
        ("invoice_lines", ("amount_usd",)),
        ("payments", ("amount_usd",)),
    ):
        for column in columns:
            op.alter_column(
                table,
                column,
                existing_type=sa.Numeric(12, 4),
                type_=sa.Numeric(10, 2),
                existing_nullable=False,
            )
