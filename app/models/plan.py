from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.device_service import DeviceService
    from app.models.subscription import Subscription


class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    name: str = Field(
        sa_column=Column(String(100), unique=True, nullable=False, index=True)
    )
    description: Optional[str] = Field(default=None, max_length=500)
    price_monthly: Decimal = Field(
        sa_column=Column(
            String, nullable=False
        )  # Stored as string to avoid precision issues
    )
    price_yearly: Decimal = Field(sa_column=Column(String, nullable=False))
    max_devices: int = Field(sa_column=Column(Integer, default=1, nullable=False))
    history_days: int = Field(sa_column=Column(Integer, default=7, nullable=False))
    ai_features: bool = Field(sa_column=Column(Boolean, default=False, nullable=False))
    analytics_tools: bool = Field(
        sa_column=Column(Boolean, default=False, nullable=False)
    )
    features: Optional[dict] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
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
    subscriptions: list["Subscription"] = Relationship(back_populates="plan")
    device_services: list["DeviceService"] = Relationship(back_populates="plan")
