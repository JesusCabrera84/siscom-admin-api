"""Restructure devices table and add device_events

Revision ID: 006_devices_events
Revises: 005_rename_device_id
Create Date: 2025-11-06

Cambios principales:
- Cambia device_id como PRIMARY KEY (elimina id UUID)
- client_id ahora es nullable
- Reemplaza 'active' por 'status' con múltiples estados
- Agrega firmware_version, last_assignment_at, notes
- Crea tabla device_events para historial
- Agrega trigger para prevenir eliminación de dispositivos
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "006_devices_events"
down_revision = "005_rename_device_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Reestructura la tabla devices y crea device_events.
    ADVERTENCIA: Esta migración ELIMINA la tabla devices existente y la recrea vacía.
    """
    
    # ============================================
    # PASO 1: Verificar existencia de tablas dependientes
    # ============================================
    result = op.get_bind().execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'device_services'
        )
    """))
    device_services_exists = result.scalar()
    
    result = op.get_bind().execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'order_items'
        )
    """))
    order_items_exists = result.scalar()
    
    # ============================================
    # PASO 2: Eliminar constraints de order_items que dependen de devices
    # ============================================
    if order_items_exists:
        # Eliminar foreign key constraint de order_items.device_id
        op.execute("""
            ALTER TABLE order_items 
            DROP CONSTRAINT IF EXISTS order_items_device_id_fkey CASCADE
        """)
    
    # ============================================
    # PASO 3: Eliminar tablas dependientes
    # ============================================
    if device_services_exists:
        op.drop_table("device_services")
    
    # ============================================
    # PASO 4: Eliminar tabla devices antigua con CASCADE
    # ============================================
    op.execute("DROP TABLE IF EXISTS devices CASCADE")
    
    # ============================================
    # PASO 5: Crear nueva tabla devices con estructura correcta
    # ============================================
    op.execute("""
        CREATE TABLE devices (
            device_id TEXT PRIMARY KEY,
            brand TEXT,
            model TEXT,
            firmware_version TEXT,
            client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'nuevo' 
                CHECK (status IN (
                    'nuevo',
                    'enviado',
                    'entregado',
                    'asignado',
                    'devuelto',
                    'inactivo'
                )),
            installed_in_unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
            last_comm_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            last_assignment_at TIMESTAMP WITH TIME ZONE,
            notes TEXT
        )
    """)
    
    # ============================================
    # PASO 6: Crear índices recomendados
    # ============================================
    op.create_index("idx_devices_status", "devices", ["status"])
    op.create_index("idx_devices_client_id", "devices", ["client_id"])
    op.create_index("idx_devices_brand_model", "devices", ["brand", "model"])
    
    # ============================================
    # PASO 7: Crear tabla device_events
    # ============================================
    op.create_table(
        "device_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", sa.Text(), sa.ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("old_status", sa.Text(), nullable=True),
        sa.Column("new_status", sa.Text(), nullable=True),
        sa.Column("performed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    
    # Agregar constraint para event_type
    op.execute("""
        ALTER TABLE device_events 
        ADD CONSTRAINT check_event_type 
        CHECK (event_type IN (
            'creado',
            'enviado',
            'entregado',
            'asignado',
            'devuelto',
            'firmware_actualizado',
            'nota',
            'estado_cambiado'
        ))
    """)
    
    # ============================================
    # PASO 8: Crear índices para device_events
    # ============================================
    op.create_index("idx_device_events_device_id", "device_events", ["device_id"])
    op.create_index("idx_device_events_created_at", "device_events", ["created_at"])
    op.create_index("idx_device_events_event_type", "device_events", ["event_type"])
    
    # ============================================
    # PASO 9: Crear trigger para prevenir DELETE
    # ============================================
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_device_delete()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'No se permite eliminar dispositivos del inventario';
        END;
        $$ LANGUAGE plpgsql
    """)
    
    op.execute("""
        CREATE TRIGGER trg_no_delete_devices
        BEFORE DELETE ON devices
        FOR EACH ROW EXECUTE FUNCTION prevent_device_delete()
    """)
    
    # ============================================
    # PASO 10: Recrear device_services con nueva estructura (si existía)
    # ============================================
    if device_services_exists:
        # Crear device_services con la nueva referencia a devices.device_id
        op.execute("""
            CREATE TABLE device_services (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                device_id TEXT REFERENCES devices(device_id) NOT NULL,
                client_id UUID REFERENCES clients(id) NOT NULL,
                plan_id UUID REFERENCES plans(id) NOT NULL,
                subscription_id UUID REFERENCES subscriptions(id),
                subscription_type VARCHAR NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'ACTIVE',
                activated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                expires_at TIMESTAMP WITH TIME ZONE,
                renewed_at TIMESTAMP WITH TIME ZONE,
                cancelled_at TIMESTAMP WITH TIME ZONE,
                auto_renew BOOLEAN DEFAULT true NOT NULL,
                payment_id UUID REFERENCES payments(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """)
        
        # Recrear índices
        op.create_index("idx_device_services_device", "device_services", ["device_id"])
        op.create_index("idx_device_services_client", "device_services", ["client_id"])
        op.create_index("idx_device_services_status", "device_services", ["status"])
    
    # ============================================
    # PASO 11: Actualizar order_items para usar device_id TEXT (si existía)
    # ============================================
    if order_items_exists:
        # Cambiar device_id de UUID a TEXT y recrear foreign key
        op.execute("""
            ALTER TABLE order_items 
            ALTER COLUMN device_id TYPE TEXT USING device_id::TEXT
        """)
        
        # Recrear constraint con la nueva estructura
        op.execute("""
            ALTER TABLE order_items 
            ADD CONSTRAINT order_items_device_id_fkey 
            FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE SET NULL
        """)
    
    # No hay datos que migrar, las tablas están vacías


def downgrade() -> None:
    """
    Revierte los cambios: restaura estructura antigua de devices y elimina device_events.
    ADVERTENCIA: Esta operación puede causar pérdida de datos.
    """
    
    # Eliminar trigger
    op.execute("DROP TRIGGER IF EXISTS trg_no_delete_devices ON devices")
    op.execute("DROP FUNCTION IF EXISTS prevent_device_delete()")
    
    # Eliminar tabla device_events
    op.drop_table("device_events")
    
    # Crear tabla devices con estructura antigua
    op.execute("""
        CREATE TABLE devices_old (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID REFERENCES clients(id) NOT NULL,
            device_id VARCHAR(50) UNIQUE NOT NULL,
            brand VARCHAR(100),
            model VARCHAR(100),
            active BOOLEAN NOT NULL DEFAULT true,
            installed_in_unit_id UUID REFERENCES units(id),
            last_comm_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)
    
    # Migrar datos de vuelta (solo dispositivos con client_id)
    op.execute("""
        INSERT INTO devices_old (
            client_id, device_id, brand, model, active,
            installed_in_unit_id, last_comm_at, created_at, updated_at
        )
        SELECT 
            client_id,
            device_id,
            brand,
            model,
            CASE 
                WHEN status IN ('nuevo', 'enviado', 'entregado', 'asignado', 'devuelto') THEN true
                ELSE false
            END as active,
            installed_in_unit_id,
            last_comm_at,
            created_at,
            updated_at
        FROM devices
        WHERE client_id IS NOT NULL
    """)
    
    # Eliminar tabla nueva
    op.drop_table("devices")
    
    # Renombrar tabla antigua
    op.rename_table("devices_old", "devices")
    
    # Recrear índices originales
    op.create_index("idx_devices_client", "devices", ["client_id"])
    op.create_index("idx_devices_device_id", "devices", ["device_id"])

