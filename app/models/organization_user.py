"""
Modelo para roles organizacionales.

Define la relación entre usuarios y organizaciones con roles específicos.
Reemplaza conceptualmente la dependencia de is_master.

Basado en DDL: public.organization_users
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class OrganizationRole(str, enum.Enum):
    """
    Roles disponibles dentro de una organización.
    
    - owner: Control total, único por organización
    - admin: Gestión de usuarios, configuración
    - billing: Pagos, suscripciones, facturación
    - member: Acceso operativo según permisos asignados
    """
    OWNER = "owner"
    ADMIN = "admin"
    BILLING = "billing"
    MEMBER = "member"


class OrganizationUser(SQLModel, table=True):
    """
    Relación usuario-organización con rol asignado.
    
    Un usuario puede pertenecer a una organización con un rol específico.
    Este modelo es la fuente de verdad para permisos organizacionales.
    """
    __tablename__ = "organization_users"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
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
        )
    )
    user_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    role: OrganizationRole = Field(
        default=OrganizationRole.MEMBER,
        sa_column=Column(
            String,
            nullable=False,
            default=OrganizationRole.MEMBER.value,
        )
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=True
        )
    )

    # Relationships
    organization: "Organization" = Relationship(back_populates="organization_users")
    user: "User" = Relationship(back_populates="organization_memberships")

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

    def can_manage_users(self) -> bool:
        """Verifica si el rol puede gestionar usuarios."""
        return self.role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]

    def can_manage_billing(self) -> bool:
        """Verifica si el rol puede gestionar facturación."""
        return self.role in [OrganizationRole.OWNER, OrganizationRole.BILLING]

    def can_manage_organization(self) -> bool:
        """Verifica si el rol puede gestionar la organización."""
        return self.role == OrganizationRole.OWNER

    def is_owner(self) -> bool:
        """Verifica si es el owner de la organización."""
        return self.role == OrganizationRole.OWNER
