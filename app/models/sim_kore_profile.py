"""
Modelo para perfiles de SIM KORE.

Esta tabla almacena los datos específicos de SIM cards
del proveedor KORE Wireless (SuperSIM).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.sim_card import SimCard


class SimKoreProfile(SQLModel, table=True):
    """
    Perfil específico para SIM cards de KORE Wireless.

    Contiene el kore_sim_id necesario para enviar comandos SMS
    a través de la API de KORE SuperSIM.

    Nota: sim_id es tanto PK como FK a sim_cards (relación 1:1).
    """

    __tablename__ = "sim_kore_profiles"

    # sim_id es PK y FK a la vez (relación 1:1 con sim_cards)
    sim_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("sim_cards.sim_id"),
            primary_key=True,
        )
    )

    kore_sim_id: str = Field(
        sa_column=Column(Text, nullable=False),
        description="ID de la SIM en KORE (ej: HS0ad6bc269850dfe13bc8bddfcf8399f4)",
    )

    kore_account_id: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="ID de cuenta en KORE (ej: CO1757099...)",
    )

    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("now()"),
            nullable=True,
        ),
    )

    # Relationship
    sim_card: "SimCard" = Relationship(back_populates="kore_profile")
