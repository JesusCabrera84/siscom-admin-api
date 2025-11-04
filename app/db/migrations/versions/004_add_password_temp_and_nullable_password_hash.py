"""Add password_temp to tokens_confirmacion and make password_hash nullable

Revision ID: 004
Revises: 003
Create Date: 2025-11-03

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    1. Hace password_hash nullable en users (ya que usamos Cognito)
    2. Agrega password_temp a tokens_confirmacion para guardar contraseñas temporalmente
    """
    # 1. Hacer password_hash nullable en users
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
        existing_nullable=False,
    )

    # 2. Agregar password_temp a tokens_confirmacion
    op.add_column(
        "tokens_confirmacion",
        sa.Column("password_temp", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """
    Revierte los cambios.
    """
    # Eliminar password_temp de tokens_confirmacion
    op.drop_column("tokens_confirmacion", "password_temp")

    # Hacer password_hash NOT NULL en users
    # ADVERTENCIA: Esto fallará si hay usuarios con password_hash NULL
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
        existing_nullable=True,
    )
