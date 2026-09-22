"""Initial KoiCloud schema freeze.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-22 20:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

user_role = postgresql.ENUM("client", "admin", name="user_role")
user_status = postgresql.ENUM("active", "suspended", name="user_status")
email_token_kind = postgresql.ENUM("verify_email", "reset_password", name="email_token_kind")
subscription_status = postgresql.ENUM(
    "active", "canceled", "expired", "past_due", name="subscription_status"
)
invoice_status = postgresql.ENUM("issued", "paid", "void", name="invoice_status")
payment_status = postgresql.ENUM("succeeded", "failed", "pending", name="payment_status")
node_status = postgresql.ENUM("alive", "draining", "dead", name="node_status")
pond_desired_state = postgresql.ENUM("running", "stopped", "deleted", name="pond_desired_state")
pond_observed_state = postgresql.ENUM(
    "pending",
    "provisioning",
    "running",
    "stopped",
    "restoring",
    "deleting",
    "deleted",
    "failed",
    name="pond_observed_state",
)
job_type = postgresql.ENUM(
    "create_pond",
    "start_pond",
    "stop_pond",
    "delete_pond",
    "backup_pond",
    "restore_pond",
    name="job_type",
)
job_status = postgresql.ENUM("queued", "running", "succeeded", "failed", "lost", name="job_status")
backup_kind = postgresql.ENUM("daily", "on_demand", "pre_delete", name="backup_kind")
backup_status = postgresql.ENUM("queued", "running", "succeeded", "failed", name="backup_status")
sql_mode = postgresql.ENUM("read", "write", name="sql_mode")


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    for enum in (
        user_role,
        user_status,
        email_token_kind,
        subscription_status,
        invoice_status,
        payment_status,
        node_status,
        pond_desired_state,
        pond_observed_state,
        job_type,
        job_status,
        backup_kind,
        backup_status,
        sql_mode,
    ):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default=sa.text("'client'")),
        sa.Column("nit", sa.Text(), nullable=True),
        sa.Column("status", user_status, nullable=False, server_default=sa.text("'active'")),
        sa.Column("email_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("email", name="users_email_uk"),
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price_monthly_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_ponds", sa.Integer(), nullable=False),
        sa.Column("max_storage_gb", sa.Integer(), nullable=False),
        sa.Column("validity_minutes", sa.Integer(), nullable=False),
        sa.Column("postpaid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "nodes",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("public_host", sa.Text(), nullable=False),
        sa.Column("status", node_status, nullable=False, server_default=sa.text("'alive'")),
        sa.Column("capacity_ponds", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.UniqueConstraint("token_hash", name="nodes_token_hash_uk"),
    )

    op.create_table(
        "email_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", email_token_kind, nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="email_tokens_token_hash_uk"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="refresh_tokens_token_hash_uk"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column(
            "status",
            subscription_status,
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("current_period_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
    )

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subtotal_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("iva_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", invoice_status, nullable=False, server_default=sa.text("'issued'")),
        sa.Column("issued_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.UniqueConstraint("number", name="invoices_number_uk"),
    )

    op.create_table(
        "invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", payment_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "ponds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.Column(
            "desired_state",
            pond_desired_state,
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("host_port", sa.Integer(), nullable=False),
        sa.Column("db_password_encrypted", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_restore_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.UniqueConstraint("host_port", name="ponds_host_port_uk"),
    )

    op.create_table(
        "pond_status",
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "observed_state",
            pond_observed_state,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("healthy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["pond_id"], ["ponds.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("type", job_type, nullable=False),
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=True),
        sa.Column("status", job_status, nullable=False, server_default=sa.text("'queued'")),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("claimed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["pond_id"], ["ponds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
    )

    op.create_table(
        "backups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", backup_kind, nullable=False),
        sa.Column("status", backup_status, nullable=False, server_default=sa.text("'queued'")),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pond_id"], ["ponds.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "pond_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("container_state", sa.Text(), nullable=False),
        sa.Column("sampled_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pond_id"], ["ponds.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "usage_daily",
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("instance_hours", sa.Numeric(12, 4), nullable=False),
        sa.Column("storage_gb_hours", sa.Numeric(12, 4), nullable=False),
        sa.ForeignKeyConstraint(["pond_id"], ["ponds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pond_id", "day", name="usage_daily_pk"),
    )

    op.create_table(
        "sql_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_truncated", sa.Text(), nullable=False),
        sa.Column("mode", sql_mode, nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pond_id"], ["ponds.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "agent_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_slug", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rotated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="agent_access_user_id_uk"),
        sa.UniqueConstraint("access_slug", name="agent_access_access_slug_uk"),
    )

    op.create_table(
        "pending_confirmations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="pending_confirmations_token_hash_uk"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_kind", sa.Text(), nullable=False),
        sa.Column("target_kind", sa.Text(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index(
        "ponds_user_name_uk",
        "ponds",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("desired_state <> 'deleted'::pond_desired_state"),
    )
    op.create_index(
        "jobs_one_active",
        "jobs",
        ["pond_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued'::job_status, 'running'::job_status)"),
    )
    op.create_index(
        "jobs_queue",
        "jobs",
        ["status", "created_at"],
        postgresql_where=sa.text("status = 'queued'::job_status"),
    )
    op.create_index(
        "jobs_lost_scan",
        "jobs",
        ["status", "claimed_at"],
        postgresql_where=sa.text("status = 'running'::job_status"),
    )
    op.create_index(
        "pending_conf_user_recent",
        "pending_confirmations",
        ["user_id", "expires_at"],
    )
    op.create_index("agent_access_slug_uk", "agent_access", ["access_slug"], unique=True)
    op.create_index(
        "sql_history_user_time",
        "sql_history",
        ["user_id", sa.text("executed_at DESC")],
    )
    op.create_index(
        "pond_samples_pond_time",
        "pond_samples",
        ["pond_id", sa.text("sampled_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("pond_samples_pond_time", table_name="pond_samples")
    op.drop_index("sql_history_user_time", table_name="sql_history")
    op.drop_index("agent_access_slug_uk", table_name="agent_access")
    op.drop_index("pending_conf_user_recent", table_name="pending_confirmations")
    op.drop_index("jobs_lost_scan", table_name="jobs")
    op.drop_index("jobs_queue", table_name="jobs")
    op.drop_index("jobs_one_active", table_name="jobs")
    op.drop_index("ponds_user_name_uk", table_name="ponds")

    for table_name in (
        "audit_events",
        "pending_confirmations",
        "agent_access",
        "sql_history",
        "usage_daily",
        "pond_samples",
        "backups",
        "jobs",
        "pond_status",
        "ponds",
        "payments",
        "invoice_lines",
        "invoices",
        "subscriptions",
        "refresh_tokens",
        "email_tokens",
        "nodes",
        "plans",
        "users",
    ):
        op.drop_table(table_name)

    bind = op.get_bind()
    for enum in (
        sql_mode,
        backup_status,
        backup_kind,
        job_status,
        job_type,
        pond_observed_state,
        pond_desired_state,
        node_status,
        payment_status,
        invoice_status,
        subscription_status,
        email_token_kind,
        user_status,
        user_role,
    ):
        enum.drop(bind, checkfirst=True)
