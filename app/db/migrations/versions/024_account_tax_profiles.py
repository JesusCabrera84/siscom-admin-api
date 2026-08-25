"""Perfil fiscal SAT por cuenta para Facturapi.

Revision ID: 024_account_tax_profiles
Revises: 023_payment_methods_schema
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "024_account_tax_profiles"
down_revision = "023_payment_methods_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_tax_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfc", sa.Text(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("tax_system", sa.Text(), nullable=False),
        sa.Column("zip", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("default_cfdi_use", sa.Text(), nullable=False, server_default="G03"),
        sa.Column("facturapi_customer_id", sa.Text(), nullable=True),
        sa.Column(
            "facturapi_livemode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", name="uq_account_tax_profiles_account"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("account_tax_profiles", schema="public")
