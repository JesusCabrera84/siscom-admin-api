"""
Schemas para Clientes/Organizaciones.

NOTA: "Client" es un alias de compatibilidad para "Organization".
Este archivo se mantiene para no romper endpoints existentes.

Para código nuevo, usar app/schemas/organization.py

El modelo conceptual actual es:
- Account = Raíz comercial (billing)
- Organization = Raíz operativa (permisos, uso diario)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.organization import OrganizationStatus
from app.utils.validators import validate_name, validate_password


# Alias de compatibilidad (DEPRECATED)
ClientStatus = OrganizationStatus


class ClientBase(BaseModel):
    """Base para un cliente/organización. DEPRECATED: Usar OrganizationBase."""
    name: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE


class ClientOut(ClientBase):
    """
    Cliente/Organización en respuestas.
    DEPRECATED: Usar OrganizationOut.
    
    Nota: active_subscription_id está DEPRECADO.
    Las suscripciones activas se calculan dinámicamente.
    """
    id: UUID
    account_id: Optional[UUID] = None
    billing_email: Optional[str] = None
    country: Optional[str] = None
    timezone: str = "UTC"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "223e4567-e89b-12d3-a456-426614174000",
                "name": "Transportes García",
                "status": "ACTIVE",
                "billing_email": "facturacion@transportesgarcia.com",
                "country": "MX",
                "timezone": "America/Mexico_City",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class ClientCreate(BaseModel):
    """
    Schema para crear un cliente/organización con usuario owner.
    
    NOTA: Ahora en el onboarding se crea:
    1. Account (raíz comercial)
    2. Organization (pertenece a Account)
    3. User (owner de Organization)
    """
    name: str = Field(..., min_length=1, description="Nombre de la organización")
    email: EmailStr = Field(..., description="Correo electrónico del owner")
    password: str = Field(..., min_length=8, description="Contraseña del owner")

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        """Valida la contraseña usando el validador reutilizable."""
        return validate_password(v)

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        """Valida el nombre usando el validador reutilizable."""
        return validate_name(v)


class ClientUpdate(BaseModel):
    """Schema para actualizar un cliente/organización."""
    name: Optional[str] = Field(None, min_length=1, description="Nombre de la organización")
    billing_email: Optional[EmailStr] = Field(None, description="Email de facturación")
    country: Optional[str] = Field(None, max_length=2, description="Código de país ISO")
    timezone: Optional[str] = Field(None, description="Zona horaria (ej: America/Mexico_City)")

    class Config:
        json_schema_extra = {
            "example": {
                "billing_email": "nueva-facturacion@empresa.com",
                "timezone": "America/Mexico_City",
            }
        }


# Alias para compatibilidad con imports existentes
OrganizationBase = ClientBase
OrganizationCreate = ClientCreate
