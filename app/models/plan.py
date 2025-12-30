"""
Modelo de Plan.

Los planes definen las capabilities base disponibles para las organizaciones.
Las capabilities específicas se definen en plan_capabilities.

NOTA: Los campos max_devices, history_days, ai_features, analytics_tools
están DEPRECADOS. Usar el sistema de capabilities (plan_capabilities).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.capability import PlanCapability
    from app.models.device_service import DeviceService
    from app.models.subscription import Subscription


class Plan(SQLModel, table=True):
    """
    Plan de suscripción del sistema.

    Define el precio y las capabilities base.
    Las capabilities específicas se configuran en plan_capabilities.
    """

    __tablename__ = "plans"

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    name: str = Field(sa_column=Column(Text, unique=True, nullable=False))
    code: str = Field(
        sa_column=Column(Text, unique=True, nullable=False),
        description="Código único del plan (ej: 'basic', 'pro', 'enterprise')",
    )
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    price_monthly: Decimal = Field(
        sa_column=Column(Numeric(10, 2), default=0, nullable=False)
    )
    price_yearly: Decimal = Field(
        sa_column=Column(Numeric(10, 2), default=0, nullable=False)
    )

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=text("now()"), nullable=True),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=text("now()"), nullable=True),
    )

    # Relationships
    subscriptions: list["Subscription"] = Relationship(back_populates="plan")
    device_services: list["DeviceService"] = Relationship(back_populates="plan")
    plan_capabilities: list["PlanCapability"] = Relationship(back_populates="plan")
