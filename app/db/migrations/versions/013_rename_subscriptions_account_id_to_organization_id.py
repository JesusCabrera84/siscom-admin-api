"""Rename subscriptions.account_id to organization_id

Revision ID: 013_rename_subscriptions_account_id
Revises: 012_add_account_id_to_organizations
Create Date: 2025-12-29

Cambios principales:
- Renombra subscriptions.account_id -> organization_id
- Actualiza FK para apuntar correctamente a organizations.id
- Actualiza índices

CONTEXTO:
    La columna subscriptions.account_id existía pero su FK apuntaba a organizations.
    Esto era confuso. Ahora se renombra a organization_id para claridad.

MODELO:
    Organization 1 ──< Subscription *
    (Una organización puede tener múltiples suscripciones)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "013_rename_subscriptions_account_id"
down_revision = "012_add_account_id_to_organizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Renombra account_id a organization_id en subscriptions
    """
    conn = op.get_bind()

    # ============================================
    # PASO 1: Verificar estado actual
    # ============================================
    # Verificar si ya existe organization_id
    result = conn.execute(
        sa.text(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions' AND column_name = 'organization_id'
            """
        )
    )
    if result.fetchone():
        print("✅ subscriptions.organization_id ya existe, saltando migración")
        return

    # Verificar si existe account_id
    result = conn.execute(
        sa.text(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions' AND column_name = 'account_id'
            """
        )
    )
    if not result.fetchone():
        print("⚠️ subscriptions.account_id no existe, creando organization_id directamente")
        op.add_column(
            "subscriptions",
            sa.Column("organization_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            "subscriptions_organization_id_fkey",
            "subscriptions",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            "idx_subscriptions_organization_id",
            "subscriptions",
            ["organization_id"],
        )
        return

    # ============================================
    # PASO 2: Eliminar FK existente (apunta a organizations con nombre confuso)
    # ============================================
    # La FK existente se llama subscriptions_organization_id_fkey pero usa account_id
    try:
        op.drop_constraint(
            "subscriptions_organization_id_fkey",
            "subscriptions",
            type_="foreignkey",
        )
    except Exception:
        # Puede que no exista con ese nombre
        pass

    try:
        op.drop_constraint(
            "subscriptions_account_id_fkey",
            "subscriptions",
            type_="foreignkey",
        )
    except Exception:
        pass

    # ============================================
    # PASO 3: Eliminar índices existentes
    # ============================================
    try:
        op.drop_index("idx_subscriptions_client", table_name="subscriptions")
    except Exception:
        pass

    try:
        op.drop_index("idx_subscriptions_organization_id", table_name="subscriptions")
    except Exception:
        pass

    # ============================================
    # PASO 4: Renombrar columna
    # ============================================
    op.alter_column(
        "subscriptions",
        "account_id",
        new_column_name="organization_id",
    )

    # ============================================
    # PASO 5: Crear nueva FK con nombre correcto
    # ============================================
    op.create_foreign_key(
        "subscriptions_organization_id_fkey",
        "subscriptions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ============================================
    # PASO 6: Crear índice
    # ============================================
    op.create_index(
        "idx_subscriptions_organization_id",
        "subscriptions",
        ["organization_id"],
    )

    print("✅ Migración completada: subscriptions.account_id -> organization_id")


def downgrade() -> None:
    """
    Revierte el renombramiento (organization_id -> account_id)
    """
    # Eliminar índice
    try:
        op.drop_index("idx_subscriptions_organization_id", table_name="subscriptions")
    except Exception:
        pass

    # Eliminar FK
    try:
        op.drop_constraint(
            "subscriptions_organization_id_fkey",
            "subscriptions",
            type_="foreignkey",
        )
    except Exception:
        pass

    # Renombrar columna de vuelta
    op.alter_column(
        "subscriptions",
        "organization_id",
        new_column_name="account_id",
    )

    # Recrear FK (aunque con nombre confuso, por compatibilidad)
    op.create_foreign_key(
        "subscriptions_organization_id_fkey",
        "subscriptions",
        "organizations",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Recrear índice
    op.create_index(
        "idx_subscriptions_client",
        "subscriptions",
        ["account_id"],
    )

