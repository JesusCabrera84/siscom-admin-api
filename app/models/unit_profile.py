from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.unit import Unit
    from app.models.vehicle_profile import VehicleProfile


class UnitProfile(SQLModel, table=True):
    """
    Perfil de unidad (universal) que almacena información adicional
    de la unidad como marca, modelo, color, año, etc.
    """

    __tablename__ = "unit_profile"

    profile_id: UUID = Field(
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
            nullable=False,
            unique=True,
        ),
    )
    unit_type: str = Field(sa_column=Column(Text, nullable=False))
    icon_type: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    brand: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    model: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    serial: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    color: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    year: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
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
    unit: "Unit" = Relationship(back_populates="unit_profile")
    vehicle_profile: Optional["VehicleProfile"] = Relationship(
        back_populates="unit_profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )
