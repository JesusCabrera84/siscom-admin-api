"""Create tokens_confirmacion table and remove verification_token from users

Revision ID: 002_tokens_table
Revises: 001_update_user
Create Date: 2025-11-02 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_tokens_table"
down_revision: Union[str, None] = "001_update_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ Crear tabla tokens_confirmacion solo si no existe
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens_confirmacion (
            id UUID DEFAULT gen_random_uuid() NOT NULL,
            token VARCHAR NOT NULL,
            expires_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() + interval '1 hour') NOT NULL,
            used BOOLEAN DEFAULT false NOT NULL,
            type VARCHAR DEFAULT 'email_verification' NOT NULL,
            user_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT tokens_confirmacion_pkey PRIMARY KEY (id),
            CONSTRAINT tokens_confirmacion_token_key UNIQUE (token),
            CONSTRAINT tokens_confirmacion_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """
    )

    # Crear índice en la columna token si no existe
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_tokens_confirmacion_token') THEN
                CREATE INDEX idx_tokens_confirmacion_token ON tokens_confirmacion(token);
            END IF;
        END $$;
    """
    )

    # 2️⃣ Eliminar el índice y columna verification_token de users si existen
    op.execute("DROP INDEX IF EXISTS idx_users_verification_token")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='users' AND column_name='verification_token') THEN
                ALTER TABLE users DROP COLUMN verification_token;
            END IF;
        END $$;
    """
    )


def downgrade() -> None:
    # 1️⃣ Recrear columna verification_token en users
    op.add_column(
        "users", sa.Column("verification_token", sa.String(255), nullable=True)
    )
    op.create_index(
        "idx_users_verification_token", "users", ["verification_token"], unique=True
    )

    # 2️⃣ Eliminar tabla tokens_confirmacion
    op.drop_index("idx_tokens_confirmacion_token", "tokens_confirmacion")
    op.drop_table("tokens_confirmacion")
