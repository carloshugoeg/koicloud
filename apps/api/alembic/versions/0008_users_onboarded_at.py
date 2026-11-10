"""Add users.onboarded_at for one-time plans onboarding.

Revision ID: 0008_users_onboarded_at
Revises: 0007_temp_sql_confirm
Create Date: 2026-11-10 18:20:00

W1-54 demo P0: nullable timestamptz set once when the user finishes the
first-login plan chooser (Continuar gratis or paid subscribe). Exposed as
UserOut.onboarded. Minimal contract + schema change required so the SPA can
gate after reload without localStorage.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008_users_onboarded_at"
down_revision = "0007_temp_sql_confirm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Existing accounts skip the one-time chooser; only post-migration registers
    # start with NULL and see /app/onboarding once.
    op.execute("UPDATE users SET onboarded_at = created_at WHERE onboarded_at IS NULL")


def downgrade() -> None:
    op.drop_column("users", "onboarded_at")
