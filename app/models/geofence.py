from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import BIGINT, TIMESTAMP, Boolean, Column, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class Geofence(SQLModel, table=True):
    """Geocerca por organizacion construida con indices H3."""

    __tablename__ = "geofences"

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
            nullable=False,
        )
    )

    created_by: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            nullable=False,
        )
    )

    name: str = Field(sa_column=Column(Text, nullable=False))

    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, default=True, nullable=False),
    )

    config: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
    )


class GeofenceCell(SQLModel, table=True):
    """Celdas H3 asociadas a una geocerca."""

    __tablename__ = "geofence_cells"

    geofence_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("geofences.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )

    h3_index: int = Field(
        sa_column=Column(
            BIGINT,
            primary_key=True,
            nullable=False,
        )
    )
