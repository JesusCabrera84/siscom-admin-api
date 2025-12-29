"""
Schemas para Account.

Account representa la raíz comercial del cliente.
SIEMPRE existe desde el primer registro.

Relación: Account 1 ──< Organization *
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.account import AccountStatus


class AccountBase(BaseModel):
    """Base para una cuenta."""
    name: str = Field(..., min_length=1, description="Nombre de la cuenta/empresa")


class AccountCreate(AccountBase):
    """Schema para crear una cuenta."""
    billing_email: Optional[EmailStr] = Field(None, description="Email de facturación")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Transportes García S.A.",
                "billing_email": "facturacion@transportesgarcia.com",
            }
        }


class AccountOut(AccountBase):
    """Cuenta en respuestas."""
    id: UUID
    status: AccountStatus
    billing_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Transportes García S.A.",
                "status": "ACTIVE",
                "billing_email": "facturacion@transportesgarcia.com",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class AccountUpdate(BaseModel):
    """Schema para actualizar una cuenta."""
    name: Optional[str] = Field(None, min_length=1, description="Nombre de la cuenta")
    billing_email: Optional[EmailStr] = Field(None, description="Email de facturación")

    class Config:
        json_schema_extra = {
            "example": {
                "billing_email": "nuevo-email@empresa.com",
            }
        }


class AccountWithOrganizationsOut(AccountOut):
    """Cuenta con sus organizaciones."""
    organizations_count: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Transportes García S.A.",
                "status": "ACTIVE",
                "billing_email": "facturacion@transportesgarcia.com",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "organizations_count": 1,
            }
        }

