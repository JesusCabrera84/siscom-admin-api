"""Rename users.client_id to organization_id

Revision ID: 014_rename_users_client_id
Revises: 013_rename_subscriptions_account_id
Create Date: 2025-12-29

Cambios principales:
- Renombra users.client_id -> organization_id
- Actualiza FK
- Actualiza índices

CONTEXTO:
    El campo users.client_id es un vestigio del naming antiguo.
    Aunque tiene un comentario "LEGACY", seguía siendo funcional.
    Ahora se renombra a organization_id para consistencia.

MODELO:
    Organization 1 ──< User *
    (Una organización puede tener múltiples usuarios)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "014_rename_users_client_id"
down_revision = "013_rename_subscriptions_account_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Renombra client_id a organization_id en users
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
            WHERE table_name = 'users' AND column_name = 'organization_id'
            """
        )
    )
    if result.fetchone():
        print("✅ users.organization_id ya existe, saltando migración")
        return

    # Verificar si existe client_id
    result = conn.execute(
        sa.text(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'client_id'
            """
        )
    )
    if not result.fetchone():
        print("⚠️ users.client_id no existe, nada que migrar")
        return

    # ============================================
    # PASO 2: Eliminar FK existente
    # ============================================
    try:
        op.drop_constraint(
            "users_client_id_fkey",
            "users",
            type_="foreignkey",
        )
    except Exception as e:
        print(f"⚠️ No se pudo eliminar FK users_client_id_fkey: {e}")

    # ============================================
    # PASO 3: Eliminar índices existentes
    # ============================================
    try:
        op.drop_index("idx_users_client_master", table_name="users")
    except Exception:
        pass

    # ============================================
    # PASO 4: Renombrar columna
    # ============================================
    op.alter_column(
        "users",
        "client_id",
        new_column_name="organization_id",
    )

    # ============================================
    # PASO 5: Crear nueva FK
    # ============================================
    op.create_foreign_key(
        "users_organization_id_fkey",
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ============================================
    # PASO 6: Crear índice (con is_master para compatibilidad)
    # ============================================
    op.create_index(
        "idx_users_organization_master",
        "users",
        ["organization_id", "is_master"],
    )

    # ============================================
    # PASO 7: Actualizar comentario de columna
    # ============================================
    op.execute(
        """
        COMMENT ON COLUMN public.users.organization_id IS 
        'Organization a la que pertenece el usuario. Ver organization_users para roles.';
        """
    )

    print("✅ Migración completada: users.client_id -> organization_id")


def downgrade() -> None:
    """
    Revierte el renombramiento (organization_id -> client_id)
    """
    # Eliminar índice nuevo
    try:
        op.drop_index("idx_users_organization_master", table_name="users")
    except Exception:
        pass

    # Eliminar FK nueva
    try:
        op.drop_constraint(
            "users_organization_id_fkey",
            "users",
            type_="foreignkey",
        )
    except Exception:
        pass

    # Renombrar columna de vuelta
    op.alter_column(
        "users",
        "organization_id",
        new_column_name="client_id",
    )

    # Recrear FK original
    op.create_foreign_key(
        "users_client_id_fkey",
        "users",
        "organizations",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Recrear índice original
    op.create_index(
        "idx_users_client_master",
        "users",
        ["client_id", "is_master"],
    )

    # Restaurar comentario legacy
    op.execute(
        """
        COMMENT ON COLUMN public.users.client_id IS 
        'LEGACY: organization default del usuario. No usar para permisos.';
        """
    )

