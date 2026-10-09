"""Payment port columns and pending_payment subscription status.

Revision ID: 0004_billing_payment_port
Revises: 0003_billing_invoice_money
Create Date: 2026-10-09 16:10:00

CCR: https://github.com/carloshugoeg/koicloud/issues/66
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_billing_payment_port"
down_revision = "0003_billing_invoice_money"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'pending_payment'")
    op.add_column(
        "payments",
        sa.Column("provider", sa.Text(), nullable=False, server_default="simulated"),
    )
    op.add_column(
        "payments",
        sa.Column("provider_ref", sa.Text(), nullable=False, server_default=""),
    )
    op.execute(
        """
        UPDATE payments
        SET provider = method,
            provider_ref = CASE
                WHEN provider_ref = '' OR provider_ref IS NULL THEN id::text
                ELSE provider_ref
            END
        """
    )
    op.alter_column("payments", "provider", server_default=None)
    op.alter_column("payments", "provider_ref", server_default=None)
    op.create_index("payments_provider_ref_ix", "payments", ["provider", "provider_ref"], unique=True)


def downgrade() -> None:
    op.drop_index("payments_provider_ref_ix", table_name="payments")
    op.drop_column("payments", "provider_ref")
    op.drop_column("payments", "provider")
    # Postgres cannot remove an enum value safely; leave pending_payment in place.
