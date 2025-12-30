"""
Schemas para Onboarding de Clientes.

Este módulo define los schemas para el endpoint POST /api/v1/clients
que implementa el onboarding rápido del sistema.

FLUJO DE ONBOARDING:
====================
1. Usuario proporciona datos mínimos (account_name, email, password)
2. Se crea Account (raíz comercial)
3. Se crea Organization default (raíz operativa)
4. Se crea User master
5. Se registra en Cognito
6. Se envía email de verificación

REGLA DE ORO:
=============
Los nombres NO son identidad. Los UUID sí.
❌ NO validar unicidad por account_name
❌ NO validar unicidad global por organization.name
✅ User.email debe ser único (global)
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.validators import validate_password


class OnboardingRequest(BaseModel):
    """
    Request para onboarding rápido (POST /api/v1/clients).

    Campos mínimos obligatorios:
    - account_name: Nombre de la cuenta/empresa
    - email: Email del usuario master
    - password: Contraseña del usuario master

    Campos opcionales:
    - billing_email: Email de facturación (default: email del usuario)
    - country: Código de país ISO (ej: "MX", "US")
    - timezone: Zona horaria (ej: "America/Mexico_City")
    """

    account_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre de la cuenta/empresa",
        json_schema_extra={"example": "Mi Empresa S.A."},
    )
    email: EmailStr = Field(
        ...,
        description="Email del usuario master (debe ser único globalmente)",
        json_schema_extra={"example": "usuario@ejemplo.com"},
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Contraseña del usuario master",
    )

    # Campos opcionales
    billing_email: Optional[EmailStr] = Field(
        None,
        description="Email de facturación. Si no se proporciona, usa el email del usuario.",
        json_schema_extra={"example": "facturacion@ejemplo.com"},
    )
    country: Optional[str] = Field(
        None,
        max_length=2,
        description="Código de país ISO 3166-1 alpha-2",
        json_schema_extra={"example": "MX"},
    )
    timezone: Optional[str] = Field(
        None,
        description="Zona horaria IANA",
        json_schema_extra={"example": "America/Mexico_City"},
    )

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        """Valida la contraseña usando el validador reutilizable."""
        return validate_password(v)

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, v: str) -> str:
        """Valida el nombre de la cuenta (solo limpieza, NO unicidad)."""
        v = v.strip()
        if not v:
            raise ValueError("El nombre de la cuenta no puede estar vacío")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "account_name": "Transportes García S.A.",
                "email": "admin@transportesgarcia.com",
                "password": "SecureP@ssw0rd!",
                "billing_email": "facturacion@transportesgarcia.com",
                "country": "MX",
                "timezone": "America/Mexico_City",
            }
        }


class OnboardingResponse(BaseModel):
    """
    Response del onboarding rápido.

    Retorna los IDs de las entidades creadas:
    - account_id: ID del Account creado
    - organization_id: ID de la Organization default
    - user_id: ID del User master
    """

    account_id: UUID = Field(..., description="ID del Account creado")
    organization_id: UUID = Field(..., description="ID de la Organization default")
    user_id: UUID = Field(..., description="ID del User master")

    class Config:
        json_schema_extra = {
            "example": {
                "account_id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "223e4567-e89b-12d3-a456-426614174001",
                "user_id": "323e4567-e89b-12d3-a456-426614174002",
            }
        }


# =====================================================
# SCHEMAS LEGACY (para compatibilidad con endpoints existentes)
# =====================================================

# Importar OrganizationStatus para alias de compatibilidad
from app.models.organization import OrganizationStatus

# Alias de compatibilidad (DEPRECATED)
ClientStatus = OrganizationStatus


class ClientBase(BaseModel):
    """Base para un cliente/organización. DEPRECATED: Usar OrganizationBase."""

    name: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE


class ClientOut(BaseModel):
    """
    Cliente/Organización en respuestas.

    Usado por endpoints que retornan información de Organization.
    """

    id: UUID
    account_id: Optional[UUID] = None
    name: str
    status: str
    billing_email: Optional[str] = None
    country: Optional[str] = None
    timezone: str = "UTC"
    org_metadata: Optional[dict[str, Any]] = Field(None, alias="metadata")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True
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


# =====================================================
# ALIASES DEPRECATED
# =====================================================

# Mantener compatibilidad con código existente que use estos nombres
ClientCreate = OnboardingRequest  # DEPRECATED: Usar OnboardingRequest
OrganizationBase = ClientBase  # DEPRECATED
OrganizationCreate = OnboardingRequest  # DEPRECATED
