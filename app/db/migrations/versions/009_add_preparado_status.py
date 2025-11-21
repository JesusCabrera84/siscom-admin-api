"""Add 'preparado' status to devices

Revision ID: 009_add_preparado
Revises: 008_add_deleted_at
Create Date: 2025-11-21

Cambios:
- Agrega el estado 'preparado' al CHECK constraint de devices.status
- Agrega el evento 'preparado' al CHECK constraint de device_events.event_type
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "009_add_preparado"
down_revision = "008_add_deleted_at_to_units"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Actualiza los CHECK constraints para incluir el estado 'preparado'.
    """
    
    # ============================================
    # PASO 1: Actualizar CHECK constraint de devices.status
    # ============================================
    
    # Eliminar constraint antiguo
    op.execute(
        """
        ALTER TABLE devices 
        DROP CONSTRAINT IF EXISTS devices_status_check
        """
    )
    
    # Crear nuevo constraint con 'preparado'
    op.execute(
        """
        ALTER TABLE devices 
        ADD CONSTRAINT devices_status_check 
        CHECK (status IN (
            'nuevo',
            'preparado',
            'enviado',
            'entregado',
            'asignado',
            'devuelto',
            'inactivo'
        ))
        """
    )
    
    # ============================================
    # PASO 2: Actualizar CHECK constraint de device_events.event_type
    # ============================================
    
    # Eliminar constraint antiguo
    op.execute(
        """
        ALTER TABLE device_events 
        DROP CONSTRAINT IF EXISTS check_event_type
        """
    )
    
    # Crear nuevo constraint con 'preparado'
    op.execute(
        """
        ALTER TABLE device_events 
        ADD CONSTRAINT check_event_type 
        CHECK (event_type IN (
            'creado',
            'preparado',
            'enviado',
            'entregado',
            'asignado',
            'devuelto',
            'firmware_actualizado',
            'nota',
            'estado_cambiado'
        ))
        """
    )


def downgrade() -> None:
    """
    Revierte los cambios: elimina 'preparado' de los CHECK constraints.
    """
    
    # ============================================
    # PASO 1: Revertir CHECK constraint de devices.status
    # ============================================
    
    op.execute(
        """
        ALTER TABLE devices 
        DROP CONSTRAINT IF EXISTS devices_status_check
        """
    )
    
    op.execute(
        """
        ALTER TABLE devices 
        ADD CONSTRAINT devices_status_check 
        CHECK (status IN (
            'nuevo',
            'enviado',
            'entregado',
            'asignado',
            'devuelto',
            'inactivo'
        ))
        """
    )
    
    # ============================================
    # PASO 2: Revertir CHECK constraint de device_events.event_type
    # ============================================
    
    op.execute(
        """
        ALTER TABLE device_events 
        DROP CONSTRAINT IF EXISTS check_event_type
        """
    )
    
    op.execute(
        """
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
        """
    )

