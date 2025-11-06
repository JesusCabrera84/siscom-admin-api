from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship, Index
from sqlalchemy import Column, Text, text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, TIMESTAMP

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.unit import Unit


class UserUnit(SQLModel, table=True):
    """
    Permisos de usuarios sobre unidades.
    Define qué usuarios pueden ver/editar/administrar qué unidades.
    """
    __tablename__ = "user_units"
    __table_args__ = (
        UniqueConstraint("user_id", "unit_id", name="uq_user_units_user_unit"),
        # Nota: check_user_units_role se crea en la migración SQL
        Index("idx_user_units_user_id", "user_id"),
        Index("idx_user_units_unit_id", "unit_id"),
        Index("idx_user_units_role", "role"),
    )

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    
    user_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    
    unit_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("units.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    
    granted_by: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    
    granted_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    )
    
    role: str = Field(
        default="viewer",
        sa_column=Column(Text, server_default="viewer", nullable=False)
    )

    # Relationships
    user: "User" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[UserUnit.user_id]"}
    )
    unit: "Unit" = Relationship(back_populates="user_units")
    granted_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[UserUnit.granted_by]", "lazy": "joined"}
    )
