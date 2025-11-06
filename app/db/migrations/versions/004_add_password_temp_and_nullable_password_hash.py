"""Add password_temp to tokens_confirmacion and make password_hash nullable

Revision ID: 004_password_temp
Revises: 003_invitation_fields
Create Date: 2025-11-03

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "004_password_temp"
down_revision = "003_invitation_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    1. Hace password_hash nullable en users (ya que usamos Cognito)
    2. Agrega password_temp a tokens_confirmacion para guardar contraseñas temporalmente
    """
    # 1. Hacer password_hash nullable en users (idempotente)
    op.execute(
        """
        DO $$
        BEGIN
            ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
        EXCEPTION
            WHEN others THEN NULL;
        END $$;
        """
    )

    # 2. Agregar password_temp a tokens_confirmacion (idempotente)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='tokens_confirmacion' AND column_name='password_temp') THEN
                ALTER TABLE tokens_confirmacion ADD COLUMN password_temp VARCHAR(255);
            END IF;
        END $$;
        """
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
