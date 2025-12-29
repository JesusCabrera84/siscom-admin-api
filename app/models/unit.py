from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.unit_device import UnitDevice
    from app.models.unit_profile import UnitProfile
    from app.models.user_unit import UserUnit


class Unit(SQLModel, table=True):
    """
    Unidades (vehículos, maquinaria, etc.) de la organización.
    Estructura simplificada para flexibilidad.
    """

    __tablename__ = "units"

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    organization_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    name: str = Field(sa_column=Column(Text, nullable=False))
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )

    # Relationships
    organization: "Organization" = Relationship(back_populates="units")
    unit_devices: list["UnitDevice"] = Relationship(
        back_populates="unit", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    user_units: list["UserUnit"] = Relationship(
        back_populates="unit", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    unit_profile: Optional["UnitProfile"] = Relationship(
        back_populates="unit",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )

    # Alias para compatibilidad (DEPRECATED)
    @property
    def client_id(self) -> UUID:
        """DEPRECATED: Usar organization_id"""
        return self.organization_id
    
    @client_id.setter
    def client_id(self, value: UUID):
        """DEPRECATED: Usar organization_id"""
        self.organization_id = value

    @property
    def client(self) -> "Organization":
        """DEPRECATED: Usar organization"""
        return self.organization
