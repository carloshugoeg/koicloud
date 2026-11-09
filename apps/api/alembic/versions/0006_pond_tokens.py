"""Pond-scoped temporary access tokens (issue #203 / S2 demo).

Revision ID: 0006_pond_tokens
Revises: 0005_revoked_access_tokens
Create Date: 2026-11-05 20:30:00

CCR approved by Carlos Nov 5 2026 2:23 PM GT (card t303s1220), limited to
temp-access create/list/revoke + GET /ponds/{id}/schema.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_pond_tokens"
down_revision = "0005_revoked_access_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pond_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_slug", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["pond_id"], ["ponds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("access_slug", name="pond_tokens_access_slug_uk"),
    )
    op.create_index("pond_tokens_pond_id_idx", "pond_tokens", ["pond_id"])


def downgrade() -> None:
    op.drop_index("pond_tokens_pond_id_idx", table_name="pond_tokens")
    op.drop_table("pond_tokens")
