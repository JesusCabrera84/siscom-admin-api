"""Make password_hash nullable

Revision ID: 003
Revises: 002
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Hace que el campo password_hash sea nullable.
    
    Como usamos AWS Cognito para autenticación, no necesitamos almacenar
    el password_hash en nuestra base de datos. La contraseña se maneja
    completamente en Cognito.
    """
    # Cambiar password_hash a nullable
    op.alter_column(
        'users',
        'password_hash',
        existing_type=sa.String(length=255),
        nullable=True,
        existing_nullable=False
    )


def downgrade() -> None:
    """
    Revierte el cambio haciendo password_hash NOT NULL nuevamente.
    
    ADVERTENCIA: Esto fallará si hay usuarios con password_hash NULL.
    """
    op.alter_column(
        'users',
        'password_hash',
        existing_type=sa.String(length=255),
        nullable=False,
        existing_nullable=True
    )

