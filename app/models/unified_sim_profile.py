"""
Modelo para la vista unified_sim_profiles.

Esta vista combina información de sim_cards y sim_kore_profiles
para proveer acceso unificado a los datos de SIM.

Definición de la vista:
CREATE VIEW unified_sim_profiles AS
SELECT
    sc.sim_id,
    sc.device_id,
    sc.carrier,
    sc.iccid,
    sc.msisdn,
    sc.imsi,
    sc.status,
    sk.kore_sim_id,
    sc.metadata
FROM sim_cards sc
LEFT JOIN sim_kore_profiles sk ON sc.sim_id = sk.sim_id;
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class UnifiedSimProfile(SQLModel, table=True):
    """
    Modelo de solo lectura para la vista unified_sim_profiles.

    Proporciona información combinada de sim_cards y sim_kore_profiles,
    incluyendo el kore_sim_id necesario para enviar comandos SMS via KORE.
    """

    __tablename__ = "unified_sim_profiles"

    sim_id: UUID = Field(sa_column=Column(PGUUID(as_uuid=True), primary_key=True))

    device_id: str = Field(sa_column=Column(Text, nullable=False))

    carrier: str = Field(sa_column=Column(Text, nullable=False))

    iccid: str = Field(sa_column=Column(Text, nullable=False))

    msisdn: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    imsi: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    status: str = Field(sa_column=Column(Text, nullable=False))

    # Campo de sim_kore_profiles
    kore_sim_id: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    metadata_: Optional[dict] = Field(
        default=None, sa_column=Column("metadata", JSONB, nullable=True)
    )
