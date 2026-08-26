"""Align payment_methods with the current model (method_type, is_active)

Revision ID: 023_payment_methods_schema
Revises: 022_subscription_renewal
Create Date: 2026-08-24

Las bases creadas con el DDL anterior tienen `type` y no tienen `is_active`.
El modelo y el initdb nuevo usan `method_type` + `is_active`.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "023_payment_methods_schema"
down_revision = "022_subscription_renewal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {
        c["name"] for c in inspector.get_columns("payment_methods", schema="public")
    }

    if "method_type" not in columns and "type" in columns:
        op.execute(
            sa.text(
                'ALTER TABLE public.payment_methods RENAME COLUMN "type" TO method_type'
            )
        )
    elif "method_type" not in columns:
        op.execute(
            sa.text(
                "ALTER TABLE public.payment_methods "
                "ADD COLUMN method_type public.payment_method_type "
                "NOT NULL DEFAULT 'card'"
            )
        )

    inspector = inspect(bind)
    columns = {
        c["name"] for c in inspector.get_columns("payment_methods", schema="public")
    }
    if "is_active" not in columns:
        op.add_column(
            "payment_methods",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            schema="public",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {
        c["name"] for c in inspector.get_columns("payment_methods", schema="public")
    }
    if "is_active" in columns:
        op.drop_column("payment_methods", "is_active", schema="public")
    if "method_type" in columns and "type" not in columns:
        op.execute(
            sa.text(
                'ALTER TABLE public.payment_methods RENAME COLUMN method_type TO "type"'
            )
        )
