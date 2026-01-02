"""
Modelo de Invitación.

Permite invitar usuarios a una organización con un rol específico.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Index, SQLModel


class Invitation(SQLModel, table=True):
    """
    Invitación para unirse a una organización.

    Incluye el rol que tendrá el usuario al aceptar la invitación.
    """

    __tablename__ = "invitations"
    __table_args__ = (
        Index(
            "idx_invitations_expires_at",
            "expires_at",
            postgresql_where=text("accepted = false"),
        ),
    )

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
    invited_email: str = Field(sa_column=Column(Text, nullable=False))
    invited_by_user_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    token: str = Field(sa_column=Column(Text, unique=True, nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    accepted: bool = Field(
        default=False, sa_column=Column(Boolean, default=False, nullable=True)
    )
    # Rol asignado al usuario al aceptar la invitación
    role: str = Field(
        default="member", sa_column=Column(Text, default="member", nullable=True)
    )

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=text("now()"), nullable=True),
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
