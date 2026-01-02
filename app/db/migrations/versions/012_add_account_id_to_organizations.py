"""Add account_id to organizations

Revision ID: 012_add_account_id_to_organizations
Revises: 011_sim_kore_profiles
Create Date: 2025-12-29

Cambios principales:
- Agrega columna account_id a organizations
- Crea accounts para organizations existentes (1:1)
- Establece FK organizations.account_id -> accounts.id
- Crea índice en organizations.account_id

MODELO:
    Account (raíz comercial) 1 ──< Organization (raíz operativa) *
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "012_add_account_id_to_organizations"
down_revision = "011_sim_kore_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Agrega account_id a organizations y crea accounts para existentes
    """
    conn = op.get_bind()

    # ============================================
    # PASO 1: Verificar si account_id ya existe en organizations
    # ============================================
    result = conn.execute(
        sa.text(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organizations' AND column_name = 'account_id'
            """
        )
    )
    if result.fetchone():
        print("✅ organizations.account_id ya existe, saltando migración")
        return

    # ============================================
    # PASO 2: Agregar columna account_id (nullable por ahora)
    # ============================================
    op.add_column(
        "organizations",
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            nullable=True,  # Temporalmente nullable
        ),
    )

    # ============================================
    # PASO 3: Crear accounts para organizations existentes (1:1)
    # ============================================
    # Insertamos un account por cada organization existente
    # usando el mismo ID para facilitar la migración
    op.execute(
        """
        INSERT INTO accounts (id, name, status, billing_email, created_at, updated_at)
        SELECT 
            id,  -- Mismo ID para facilitar referencia
            name,
            COALESCE(status, 'ACTIVE'),
            billing_email,
            COALESCE(created_at, now()),
            COALESCE(updated_at, now())
        FROM organizations
        WHERE id NOT IN (SELECT id FROM accounts)
        ON CONFLICT (id) DO NOTHING;
        """
    )

    # ============================================
    # PASO 4: Actualizar account_id con el mismo ID (1:1)
    # ============================================
    op.execute(
        """
        UPDATE organizations 
        SET account_id = id 
        WHERE account_id IS NULL;
        """
    )

    # ============================================
    # PASO 5: Hacer account_id NOT NULL
    # ============================================
    op.alter_column("organizations", "account_id", nullable=False)

    # ============================================
    # PASO 6: Agregar FK constraint
    # ============================================
    op.create_foreign_key(
        "organizations_account_id_fkey",
        "organizations",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ============================================
    # PASO 7: Crear índice
    # ============================================
    op.create_index(
        "idx_organizations_account_id",
        "organizations",
        ["account_id"],
    )

    print("✅ Migración completada: organizations.account_id agregado")


def downgrade() -> None:
    """
    Revierte los cambios eliminando account_id de organizations
    """
    # Eliminar índice
    op.drop_index("idx_organizations_account_id", table_name="organizations")

    # Eliminar FK
    op.drop_constraint(
        "organizations_account_id_fkey",
        "organizations",
        type_="foreignkey",
    )

    # Eliminar columna
    op.drop_column("organizations", "account_id")

    # NOTA: No eliminamos los accounts creados porque podrían tener
    # datos relacionados (payments, etc.)

