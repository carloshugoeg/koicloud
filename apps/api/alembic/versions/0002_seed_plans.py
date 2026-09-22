"""Seed initial subscription plans.

Revision ID: 0002_seed_plans
Revises: 0001_initial
Create Date: 2026-09-22 20:05:00
"""

from __future__ import annotations

from decimal import Decimal

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_seed_plans"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


plans_table = sa.table(
    "plans",
    sa.column("id", sa.Text()),
    sa.column("name", sa.Text()),
    sa.column("description", sa.Text()),
    sa.column("price_monthly_usd", sa.Numeric(10, 2)),
    sa.column("max_ponds", sa.Integer()),
    sa.column("max_storage_gb", sa.Integer()),
    sa.column("validity_minutes", sa.Integer()),
    sa.column("postpaid", sa.Boolean()),
    sa.column("active", sa.Boolean()),
)


def upgrade() -> None:
    op.bulk_insert(
        plans_table,
        [
            {
                "id": "sandbox",
                "name": "Sandbox",
                "description": "Pruebas internas (10 min)",
                "price_monthly_usd": Decimal("0.00"),
                "max_ponds": 1,
                "max_storage_gb": 1,
                "validity_minutes": 10,
                "postpaid": False,
                "active": True,
            },
            {
                "id": "micro",
                "name": "Micro",
                "description": "1 pond, 1 GB, backups 7 días",
                "price_monthly_usd": Decimal("5.00"),
                "max_ponds": 1,
                "max_storage_gb": 1,
                "validity_minutes": 30 * 24 * 60,
                "postpaid": False,
                "active": True,
            },
            {
                "id": "pro",
                "name": "Pro",
                "description": "Hasta 10 ponds, post-pago por uso",
                "price_monthly_usd": Decimal("0.00"),
                "max_ponds": 10,
                "max_storage_gb": 20,
                "validity_minutes": 30 * 24 * 60,
                "postpaid": True,
                "active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM plans WHERE id IN ('sandbox', 'micro', 'pro')")
