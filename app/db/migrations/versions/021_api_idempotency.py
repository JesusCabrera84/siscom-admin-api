"""API idempotency table, webhook processing status, failed-event index

Revision ID: 021_api_idempotency
Revises: 020_user_devices
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "021_api_idempotency"
down_revision = "020_user_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    op.execute(
        sa.text("ALTER TYPE gateway_event_status ADD VALUE IF NOT EXISTS 'processing'")
    )

    if "api_idempotency_requests" not in inspector.get_table_names(schema="public"):
        op.create_table(
            "api_idempotency_requests",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("idempotency_key", sa.Text(), nullable=False),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("endpoint", sa.Text(), nullable=False),
            sa.Column("request_hash", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("response_body", postgresql.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "expires_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now() + interval '24 hours'"),
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.UniqueConstraint(
                "idempotency_key",
                "account_id",
                "endpoint",
                name="uq_idem_account_endpoint",
            ),
            schema="public",
        )
        op.create_index(
            "idx_idem_expires",
            "api_idempotency_requests",
            ["expires_at"],
            schema="public",
        )

    indexes = {
        idx["name"]
        for idx in inspector.get_indexes("payment_gateway_events", schema="public")
    }
    if "idx_pge_failed" not in indexes:
        op.create_index(
            "idx_pge_failed",
            "payment_gateway_events",
            ["event_status", "processed_at"],
            postgresql_where=sa.text("event_status = 'failed'"),
            schema="public",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = {
        idx["name"]
        for idx in inspector.get_indexes("payment_gateway_events", schema="public")
    }
    if "idx_pge_failed" in indexes:
        op.drop_index(
            "idx_pge_failed",
            table_name="payment_gateway_events",
            schema="public",
        )
    if "api_idempotency_requests" in inspector.get_table_names(schema="public"):
        op.drop_index(
            "idx_idem_expires",
            table_name="api_idempotency_requests",
            schema="public",
        )
        op.drop_table("api_idempotency_requests", schema="public")
