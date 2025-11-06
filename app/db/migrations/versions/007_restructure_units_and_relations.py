"""Restructure units and create unit_devices relation

Revision ID: 007_units_relations
Revises: 006_devices_events
Create Date: 2025-11-06

Cambios principales:
- Simplifica tabla units (elimina plate, type, timestamps)
- Crea tabla unit_devices para relación many-to-many
- Actualiza user_units con roles y permisos mejorados
- Elimina installed_in_unit_id de devices
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "007_units_relations"
down_revision = "006_devices_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Reestructura units y crea unit_devices para relación many-to-many.
    ADVERTENCIA: Esta migración ELIMINA datos de units y user_units.
    """
    
    # ============================================
    # PASO 1: Eliminar campo installed_in_unit_id de devices
    # ============================================
    op.execute("ALTER TABLE devices DROP COLUMN IF EXISTS installed_in_unit_id CASCADE")
    
    # ============================================
    # PASO 2: Eliminar user_units antigua
    # ============================================
    op.drop_table("user_units")
    
    # ============================================
    # PASO 3: Recrear units simplificada
    # ============================================
    op.execute("DROP TABLE IF EXISTS units CASCADE")
    
    op.execute("""
        CREATE TABLE units (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT
        )
    """)
    
    # ============================================
    # PASO 4: Crear tabla unit_devices (many-to-many)
    # ============================================
    op.create_table(
        "unit_devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("unit_id", UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Text(), sa.ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("unassigned_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    
    # Agregar columna generada para is_active
    op.execute("""
        ALTER TABLE unit_devices 
        ADD COLUMN is_active BOOLEAN GENERATED ALWAYS AS (unassigned_at IS NULL) STORED
    """)
    
    # Unique constraint para evitar duplicados
    op.create_unique_constraint("uq_unit_devices_unit_device", "unit_devices", ["unit_id", "device_id"])
    
    # Índices
    op.create_index("idx_unit_devices_unit_id", "unit_devices", ["unit_id"])
    op.create_index("idx_unit_devices_device_id", "unit_devices", ["device_id"])
    op.create_index("idx_unit_devices_is_active", "unit_devices", ["is_active"])
    
    # ============================================
    # PASO 5: Recrear user_units con nueva estructura
    # ============================================
    op.create_table(
        "user_units",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("granted_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("granted_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("role", sa.Text(), server_default="viewer", nullable=False),
    )
    
    # Agregar constraint para roles
    op.execute("""
        ALTER TABLE user_units 
        ADD CONSTRAINT check_user_units_role 
        CHECK (role IN ('viewer', 'editor', 'admin'))
    """)
    
    # Unique constraint
    op.create_unique_constraint("uq_user_units_user_unit", "user_units", ["user_id", "unit_id"])
    
    # Índices
    op.create_index("idx_user_units_user_id", "user_units", ["user_id"])
    op.create_index("idx_user_units_unit_id", "user_units", ["unit_id"])
    op.create_index("idx_user_units_role", "user_units", ["role"])


def downgrade() -> None:
    """
    Revierte los cambios.
    ADVERTENCIA: Pérdida de datos.
    """
    
    # Eliminar nuevas tablas
    op.drop_table("user_units")
    op.drop_table("unit_devices")
    
    # Recrear units antigua
    op.execute("DROP TABLE IF EXISTS units CASCADE")
    op.execute("""
        CREATE TABLE units (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            client_id UUID NOT NULL REFERENCES clients(id),
            name VARCHAR(255) NOT NULL,
            plate VARCHAR(50),
            type VARCHAR(100),
            description VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)
    
    # Recrear user_units antigua
    op.execute("""
        CREATE TABLE user_units (
            user_id UUID REFERENCES users(id) PRIMARY KEY,
            unit_id UUID REFERENCES units(id) PRIMARY KEY,
            can_edit BOOLEAN DEFAULT false,
            assigned_by UUID REFERENCES users(id) NOT NULL,
            assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)
    
    # Agregar installed_in_unit_id de vuelta a devices
    op.execute("""
        ALTER TABLE devices 
        ADD COLUMN installed_in_unit_id UUID REFERENCES units(id)
    """)

