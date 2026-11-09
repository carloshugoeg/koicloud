"""Bind temporary SQL confirmations to PondToken + pond + digest.

Revision ID: 0007_temp_sql_confirm
Revises: 0006_pond_tokens
Create Date: 2026-11-08 05:50:00

CCR TEMP-CONFIRM on issue #96 (comment 6717822360). Additive nullable
binding columns on pending_confirmations. Legacy owner rows stay null-bound.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_temp_sql_confirm"
down_revision = "0006_pond_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pending_confirmations",
        sa.Column("pond_token_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pending_confirmations",
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pending_confirmations",
        sa.Column("request_digest", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "pending_confirmations_pond_token_id_fkey",
        "pending_confirmations",
        "pond_tokens",
        ["pond_token_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "pending_confirmations_pond_id_fkey",
        "pending_confirmations",
        "ponds",
        ["pond_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "pending_confirmations_temp_binding",
        "pending_confirmations",
        """
        (pond_token_id IS NULL AND pond_id IS NULL AND request_digest IS NULL)
        OR
        (
          pond_token_id IS NOT NULL AND pond_id IS NOT NULL AND request_digest IS NOT NULL
          AND action = 'run_sql_write'
          AND request_digest ~ '^[0-9a-f]{64}$'
        )
        """,
    )
    op.create_index(
        "ix_pending_confirmations_pond_token_id",
        "pending_confirmations",
        ["pond_token_id"],
        postgresql_where=sa.text("pond_token_id IS NOT NULL"),
    )


def downgrade() -> None:
    # Fail closed: never reinterpret temp-bound rows as owner grants.
    op.execute("DELETE FROM pending_confirmations WHERE pond_token_id IS NOT NULL")
    op.drop_index("ix_pending_confirmations_pond_token_id", table_name="pending_confirmations")
    op.drop_constraint("pending_confirmations_temp_binding", "pending_confirmations", type_="check")
    op.drop_constraint("pending_confirmations_pond_id_fkey", "pending_confirmations", type_="foreignkey")
    op.drop_constraint(
        "pending_confirmations_pond_token_id_fkey", "pending_confirmations", type_="foreignkey"
    )
    op.drop_column("pending_confirmations", "request_digest")
    op.drop_column("pending_confirmations", "pond_id")
    op.drop_column("pending_confirmations", "pond_token_id")
