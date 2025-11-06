from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship, Index
from sqlalchemy import Column, String, DateTime, Boolean, Text, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import enum

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.plan import Plan


class SubscriptionType(str, enum.Enum):
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class DeviceServiceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class DeviceService(SQLModel, table=True):
    __tablename__ = "device_services"
    __table_args__ = (
        Index("idx_device_services_device", "device_id"),
        Index("idx_device_services_client", "client_id"),
        Index("idx_device_services_status", "status"),
    )

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    # device_id ahora referencia a devices.device_id (TEXT) en lugar de devices.id (UUID)
    device_id: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("devices.device_id"),
            nullable=False,
        ),
    )
    client_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("clients.id"),
            nullable=False,
        ),
    )
    plan_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("plans.id"),
            nullable=False,
        ),
    )
    subscription_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True
        ),
    )
    subscription_type: SubscriptionType = Field(
        sa_column=Column(String, nullable=False)
    )
    status: DeviceServiceStatus = Field(
        sa_column=Column(
            String, default=DeviceServiceStatus.ACTIVE.value, nullable=False
        )
    )
    activated_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    renewed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    cancelled_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    auto_renew: bool = Field(sa_column=Column(Boolean, default=True, nullable=False))
    payment_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), ForeignKey("payments.id"), nullable=True
        ),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )

    # Relationships
    device: "Device" = Relationship(back_populates="device_services")
    plan: "Plan" = Relationship(back_populates="device_services")
