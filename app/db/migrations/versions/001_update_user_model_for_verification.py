"""Update user model for verification flow

Revision ID: 001_update_user
Revises: 
Create Date: 2025-11-02 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_update_user'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Modificar cognito_sub para que sea nullable
    op.alter_column('users', 'cognito_sub',
               existing_type=sa.String(255),
               nullable=True)
    
    # Agregar columnas solo si no existen (usando SQL directamente)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='users' AND column_name='email_verified') THEN
                ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='users' AND column_name='verification_token') THEN
                ALTER TABLE users ADD COLUMN verification_token VARCHAR(255);
                CREATE UNIQUE INDEX idx_users_verification_token ON users(verification_token);
            END IF;
        END $$;
    """)
    
    # Actualizar el status de clientes para incluir PENDING
    # Nota: PostgreSQL no permite ALTER TYPE directamente, necesitamos recrear el constraint
    op.execute("ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_status_check")
    op.execute("ALTER TABLE clients ADD CONSTRAINT clients_status_check CHECK (status = ANY (ARRAY['PENDING'::text, 'ACTIVE'::text, 'SUSPENDED'::text, 'DELETED'::text]))")


def downgrade() -> None:
    # Eliminar verification_token
    op.execute("DROP INDEX IF EXISTS idx_users_verification_token")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_token")
    
    # Eliminar email_verified
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
    
    # Revertir cognito_sub a NOT NULL
    op.alter_column('users', 'cognito_sub',
               existing_type=sa.String(255),
               nullable=False)
    
    # Revertir el constraint de status en clients
    op.execute("ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_status_check")
    op.execute("ALTER TABLE clients ADD CONSTRAINT clients_status_check CHECK (status = ANY (ARRAY['ACTIVE'::text, 'SUSPENDED'::text, 'DELETED'::text]))")

