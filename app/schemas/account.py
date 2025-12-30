"""
Schemas para Account.

Account representa la raíz comercial del cliente.
SIEMPRE existe desde el primer registro.

Relación: Account 1 ──< Organization *

ENDPOINTS:
==========
- PATCH /api/v1/accounts/{account_id}: Actualiza perfil de account (progresivo)

REGLA DE ORO:
=============
Los nombres NO son identidad. Los UUID sí.
❌ NO validar unicidad por account_name
✅ Solo usuarios master/owner pueden modificar
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.account import AccountStatus


class AccountBase(BaseModel):
    """Base para una cuenta."""

    name: str = Field(..., min_length=1, description="Nombre de la cuenta/empresa")


class AccountCreate(AccountBase):
    """Schema para crear una cuenta (uso interno)."""

    billing_email: Optional[EmailStr] = Field(None, description="Email de facturación")
    country: Optional[str] = Field(None, max_length=2, description="Código de país ISO")
    timezone: Optional[str] = Field(None, description="Zona horaria IANA")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Transportes García S.A.",
                "billing_email": "facturacion@transportesgarcia.com",
                "country": "MX",
                "timezone": "America/Mexico_City",
            }
        }


class AccountUpdate(BaseModel):
    """
    Schema para actualizar perfil de Account (PATCH /accounts/{id}).

    Todos los campos son opcionales para soportar perfil progresivo.
    Solo usuarios master/owner pueden usar este endpoint.

    ❌ NO se exigen campos fiscales
    ❌ NO se valida unicidad por nombre
    """

    account_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Nombre de la cuenta/empresa (puede repetirse)",
    )
    billing_email: Optional[EmailStr] = Field(
        None,
        description="Email de facturación",
    )
    country: Optional[str] = Field(
        None,
        max_length=2,
        description="Código de país ISO 3166-1 alpha-2",
    )
    timezone: Optional[str] = Field(
        None,
        description="Zona horaria IANA (ej: America/Mexico_City)",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales de la cuenta",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "account_name": "Transportes García S.A. de C.V.",
                "billing_email": "nuevo-email@empresa.com",
                "country": "MX",
                "timezone": "America/Mexico_City",
                "metadata": {
                    "rfc": "XAXX010101000",
                    "industry": "transport",
                },
            }
        }


class AccountOut(BaseModel):
    """
    Account en respuestas.

    Representa la información completa de un Account.
    """

    id: UUID
    account_name: str = Field(..., alias="name")
    status: AccountStatus
    billing_email: Optional[str] = None
    country: Optional[str] = None
    timezone: str = "UTC"
    metadata: Optional[dict[str, Any]] = Field(None, alias="account_metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_name": "Transportes García S.A.",
                "status": "ACTIVE",
                "billing_email": "facturacion@transportesgarcia.com",
                "country": "MX",
                "timezone": "America/Mexico_City",
                "metadata": {"rfc": "XAXX010101000"},
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class AccountUpdateResponse(BaseModel):
    """
    Response del endpoint PATCH /accounts/{account_id}.

    Retorna la información actualizada del Account.
    """

    id: UUID
    account_name: str
    billing_email: Optional[str] = None
    country: Optional[str] = None
    timezone: str = "UTC"
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_name": "Transportes García S.A. de C.V.",
                "billing_email": "facturacion@empresa.com",
                "country": "MX",
                "timezone": "America/Mexico_City",
                "updated_at": "2024-01-20T15:45:00Z",
            }
        }


class AccountWithOrganizationsOut(AccountOut):
    """Cuenta con información adicional sobre sus organizaciones."""

    organizations_count: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_name": "Transportes García S.A.",
                "status": "ACTIVE",
                "billing_email": "facturacion@transportesgarcia.com",
                "country": "MX",
                "timezone": "America/Mexico_City",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "organizations_count": 1,
            }
        }
