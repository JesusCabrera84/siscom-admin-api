"""Add invitation fields to tokens_confirmacion table

Revision ID: 003_invitation_fields
Revises: 002_tokens_table
Create Date: 2025-11-02 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_invitation_fields"
down_revision: Union[str, None] = "002_tokens_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega soporte para invitaciones en la tabla tokens_confirmacion:
    - Hace user_id nullable
    - Agrega email, full_name y client_id para invitaciones
    - Agrega tipo de token 'invitation'
    """
    
    # 1️⃣ Hacer user_id nullable (para soportar tokens de invitación)
    op.execute(
        """
        ALTER TABLE tokens_confirmacion 
        ALTER COLUMN user_id DROP NOT NULL
        """
    )
    
    # 2️⃣ Agregar columna email (para invitaciones)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='tokens_confirmacion' AND column_name='email') THEN
                ALTER TABLE tokens_confirmacion ADD COLUMN email VARCHAR(255) NULL;
            END IF;
        END $$;
        """
    )
    
    # 3️⃣ Agregar columna full_name (para invitaciones)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='tokens_confirmacion' AND column_name='full_name') THEN
                ALTER TABLE tokens_confirmacion ADD COLUMN full_name VARCHAR(255) NULL;
            END IF;
        END $$;
        """
    )
    
    # 4️⃣ Agregar columna client_id (para invitaciones)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='tokens_confirmacion' AND column_name='client_id') THEN
                ALTER TABLE tokens_confirmacion 
                ADD COLUMN client_id UUID NULL 
                REFERENCES clients(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    
    # 5️⃣ Crear índice en client_id para mejorar el rendimiento
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_tokens_confirmacion_client_id') THEN
                CREATE INDEX idx_tokens_confirmacion_client_id ON tokens_confirmacion(client_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """
    Revierte los cambios de invitaciones:
    - Elimina email, full_name y client_id
    - Hace user_id NOT NULL nuevamente
    """
    
    # 1️⃣ Eliminar índice de client_id
    op.execute("DROP INDEX IF EXISTS idx_tokens_confirmacion_client_id")
    
    # 2️⃣ Eliminar columnas agregadas
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='tokens_confirmacion' AND column_name='client_id') THEN
                ALTER TABLE tokens_confirmacion DROP COLUMN client_id;
            END IF;
        END $$;
        """
    )
    
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='tokens_confirmacion' AND column_name='full_name') THEN
                ALTER TABLE tokens_confirmacion DROP COLUMN full_name;
            END IF;
        END $$;
        """
    )
    
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='tokens_confirmacion' AND column_name='email') THEN
                ALTER TABLE tokens_confirmacion DROP COLUMN email;
            END IF;
        END $$;
        """
    )
    
    # 3️⃣ Hacer user_id NOT NULL nuevamente (solo si no hay tokens de invitación)
    # Primero eliminar tokens de invitación si existen
    op.execute("DELETE FROM tokens_confirmacion WHERE user_id IS NULL")
    
    op.execute(
        """
        ALTER TABLE tokens_confirmacion 
        ALTER COLUMN user_id SET NOT NULL
        """
    )

