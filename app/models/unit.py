from typing import Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, Text, text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PGUUID

if TYPE_CHECKING:
    from app.models.client import Client


class Unit(SQLModel, table=True):
    """
    Unidades (vehículos, maquinaria, etc.) del cliente.
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
    client_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    name: str = Field(sa_column=Column(Text, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )

    # Relationships
    client: "Client" = Relationship(back_populates="units")
    unit_devices: list["UnitDevice"] = Relationship(
        back_populates="unit",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    user_units: list["UserUnit"] = Relationship(
        back_populates="unit",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
