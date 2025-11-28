from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.unit_profile import UnitProfile


class VehicleProfile(SQLModel, table=True):
    """
    Perfil específico para vehículos (solo cuando unit_type = 'vehicle').
    Almacena información adicional como placa, VIN, tipo de combustible, etc.
    """

    __tablename__ = "vehicle_profile"

    unit_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("unit_profile.unit_id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    plate: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    vin: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    fuel_type: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    passengers: Optional[int] = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        )
    )

    # Relationships
    unit_profile: "UnitProfile" = Relationship(back_populates="vehicle_profile")
