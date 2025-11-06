"""Rename imei to device_id in devices table

Revision ID: 005_rename_device_id
Revises: 004_password_temp
Create Date: 2025-11-04

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005_rename_device_id"
down_revision = "004_password_temp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Renombra la columna 'imei' a 'device_id' en la tabla devices
    y actualiza el índice correspondiente.
    """
    # Eliminar el índice antiguo
    op.drop_index("idx_devices_imei", table_name="devices")

    # Renombrar la columna
    op.alter_column(
        "devices",
        "imei",
        new_column_name="device_id",
        existing_type=sa.String(length=50),
        existing_nullable=False,
    )

    # Crear el nuevo índice
    op.create_index("idx_devices_device_id", "devices", ["device_id"])


def downgrade() -> None:
    """
    Revierte el cambio: renombra 'device_id' de vuelta a 'imei'
    y restaura el índice original.
    """
    # Eliminar el índice nuevo
    op.drop_index("idx_devices_device_id", table_name="devices")

    # Renombrar la columna de vuelta
    op.alter_column(
        "devices",
        "device_id",
        new_column_name="imei",
        existing_type=sa.String(length=50),
        existing_nullable=False,
    )

    # Crear el índice original
    op.create_index("idx_devices_imei", "devices", ["imei"])
