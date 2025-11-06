from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship, Index
from sqlalchemy import Column, Text, text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, TIMESTAMP

if TYPE_CHECKING:
    from app.models.unit import Unit
    from app.models.device import Device


class UnitDevice(SQLModel, table=True):
    """
    Relación many-to-many entre Units y Devices.
    Permite que un dispositivo se asigne a una unidad y luego se desasigne.
    El campo is_active indica si la asignación está actualmente activa.
    """
    __tablename__ = "unit_devices"
    __table_args__ = (
        UniqueConstraint("unit_id", "device_id", name="uq_unit_devices_unit_device"),
        Index("idx_unit_devices_unit_id", "unit_id"),
        Index("idx_unit_devices_device_id", "device_id"),
        # Nota: idx_unit_devices_is_active se crea en la migración SQL
        # No lo definimos aquí porque is_active es una columna GENERATED
    )

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    
    unit_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("units.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    
    device_id: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("devices.device_id", ondelete="CASCADE"),
            nullable=False
        )
    )
    
    assigned_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    )
    
    unassigned_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    
    # Nota: is_active es una columna GENERATED en SQL (definida en migración)
    # No la incluimos aquí para evitar conflictos
    # Para usar: consultar directamente desde la BD o calcular: unassigned_at IS NULL

    # Relationships
    unit: "Unit" = Relationship(back_populates="unit_devices")
    device: "Device" = Relationship(back_populates="unit_devices")

