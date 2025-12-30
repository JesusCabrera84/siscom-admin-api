"""
Modelo de Usuario.

Los usuarios pertenecen a una organización (organization_id).
Los permisos se determinan por organization_users.role.

NOTA: El campo is_master está DEPRECADO.
Usar organization_users.role para permisos.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Index, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.organization_user import OrganizationUser
    from app.models.token_confirmacion import TokenConfirmacion


class User(SQLModel, table=True):
    """
    Usuario del sistema.

    Pertenece a una organización y tiene un rol definido en organization_users.
    La autenticación se maneja con AWS Cognito.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_cognito_sub", "cognito_sub"),
        Index("idx_users_organization_master", "organization_id", "is_master"),
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
    cognito_sub: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, unique=True, nullable=True, index=True),
    )
    email: str = Field(sa_column=Column(Text, unique=True, nullable=False))
    full_name: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    password_hash: Optional[str] = Field(
        default=None, sa_column=Column(Text, default="", nullable=True)
    )
    email_verified: bool = Field(
        default=False, sa_column=Column(Boolean, default=False, nullable=False)
    )
    # DEPRECADO: Usar organization_users.role
    is_master: bool = Field(
        default=False, sa_column=Column(Boolean, default=False, nullable=True)
    )
    last_login_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=text("now()"), nullable=True),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=text("now()"), nullable=True),
    )

    # Relationships
    organization: "Organization" = Relationship(back_populates="users")
    tokens: list["TokenConfirmacion"] = Relationship(back_populates="user")
    organization_memberships: list["OrganizationUser"] = Relationship(
        back_populates="user"
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

    # Alias para compatibilidad (DEPRECATED)
    @property
    def client(self) -> "Organization":
        """DEPRECATED: Usar organization"""
        return self.organization

    def get_organization_role(self, organization_id: UUID) -> Optional[str]:
        """
        Obtiene el rol del usuario en una organización específica.

        Args:
            organization_id: ID de la organización

        Returns:
            El rol del usuario o None si no pertenece a la organización
        """
        for membership in self.organization_memberships:
            if membership.organization_id == organization_id:
                return membership.role
        return None
