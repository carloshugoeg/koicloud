"""Add users.deleted_at for account soft-delete.

Revision ID: 0005_users_deleted_at
Revises: 0004_billing_payment_port
Create Date: 2026-10-27 15:30:00

CCR: https://github.com/carloshugoeg/koicloud/issues/126
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_users_deleted_at"
down_revision = "0004_billing_payment_port"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "deleted_at")
