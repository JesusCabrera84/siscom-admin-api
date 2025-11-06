"""Add deleted_at to units

Revision ID: 008_add_deleted_at_to_units
Revises: 007_units_relations
Create Date: 2025-11-06

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "008_add_deleted_at_to_units"
down_revision = "007_units_relations"
branch_labels = None
depends_on = None


def upgrade():
    """Add deleted_at column to units table for soft delete"""
    op.add_column(
        "units", sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )

    # Add index for efficient filtering of non-deleted units
    op.create_index(
        "idx_units_deleted_at",
        "units",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade():
    """Remove deleted_at column from units table"""
    op.drop_index("idx_units_deleted_at", table_name="units")
    op.drop_column("units", "deleted_at")
