from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class UserUnit(SQLModel, table=True):
    __tablename__ = "user_units"

    user_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id"),
            primary_key=True,
            nullable=False,
        ),
    )
    unit_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("units.id"),
            primary_key=True,
            nullable=False,
        ),
    )
    can_edit: bool = Field(sa_column=Column(Boolean, default=False, nullable=False))
    assigned_by: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=False,
        ),
    )
    assigned_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
