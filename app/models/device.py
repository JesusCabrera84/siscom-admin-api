from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship, Index
from sqlalchemy import Column, String, DateTime, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.unit import Unit
    from app.models.device_service import DeviceService


class Device(SQLModel, table=True):
    __tablename__ = "devices"
    __table_args__ = (
        Index("idx_devices_client", "client_id"),
        Index("idx_devices_imei", "imei"),
    )

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    client_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("clients.id"),
            nullable=False,
        ),
    )
    imei: str = Field(
        sa_column=Column(String(50), unique=True, nullable=False, index=True)
    )
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    active: bool = Field(sa_column=Column(Boolean, default=True, nullable=False))
    installed_in_unit_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=True),
    )
    last_comm_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
        )
    )

    # Relationships
    client: "Client" = Relationship(back_populates="devices")
    installed_unit: Optional["Unit"] = Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"foreign_keys": "[Device.installed_in_unit_id]"},
    )
    device_services: list["DeviceService"] = Relationship(back_populates="device")
