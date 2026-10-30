"""Revoked access-token ids.

Revision ID: 0005_revoked_access_tokens
Revises: 0004_billing_payment_port
Create Date: 2026-10-30 19:55:00

CCR: https://github.com/carloshugoeg/koicloud/issues/96 (amendment r6-7a)
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_revoked_access_tokens"
down_revision = "0004_billing_payment_port"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revoked_access_tokens",
        sa.Column("jti", sa.Text(), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("revoked_access_tokens")
