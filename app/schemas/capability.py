"""
Schemas para Capabilities.

Define los schemas de entrada/salida para el sistema de capabilities.
"""

from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class CapabilityBase(BaseModel):
    """Base para una capability."""

    code: str = Field(..., description="Código único de la capability")
    description: str = Field(..., description="Descripción de la capability")
    value_type: str = Field(..., description="Tipo de valor: int, bool, text")


class CapabilityOut(CapabilityBase):
    """Capability en respuestas."""

    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "code": "max_devices",
                "description": "Número máximo de dispositivos permitidos",
                "value_type": "int",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }


class ResolvedCapabilityOut(BaseModel):
    """
    Capability resuelta para una organización.

    Incluye el valor efectivo y la fuente de donde se obtuvo.
    """

    code: str = Field(..., description="Código de la capability")
    value: Union[int, bool, str, None] = Field(..., description="Valor resuelto")
    source: str = Field(
        ..., description="Fuente del valor: organization, plan, default"
    )
    plan_id: Optional[UUID] = Field(None, description="ID del plan si aplica")
    expires_at: Optional[datetime] = Field(
        None, description="Fecha de expiración si es override"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "max_devices",
                "value": 50,
                "source": "organization",
                "plan_id": None,
                "expires_at": "2024-12-31T23:59:59Z",
            }
        }


class CapabilitiesSummaryOut(BaseModel):
    """
    Resumen de capabilities de una organización.

    Agrupa límites y features para fácil consumo.
    """

    limits: dict[str, int] = Field(..., description="Capabilities de tipo límite")
    features: dict[str, Any] = Field(..., description="Capabilities de tipo feature")

    class Config:
        json_schema_extra = {
            "example": {
                "limits": {
                    "max_devices": 50,
                    "max_geofences": 100,
                    "max_users": 10,
                    "history_days": 90,
                },
                "features": {
                    "ai_features": True,
                    "analytics_tools": True,
                    "api_access": True,
                    "real_time_tracking": True,
                },
            }
        }


class OrganizationCapabilityCreate(BaseModel):
    """Schema para crear/actualizar un override de capability."""

    capability_code: str = Field(..., description="Código de la capability")
    value_int: Optional[int] = Field(None, description="Valor entero")
    value_bool: Optional[bool] = Field(None, description="Valor booleano")
    value_text: Optional[str] = Field(None, description="Valor texto")
    reason: Optional[str] = Field(None, description="Razón del override")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración")

    class Config:
        json_schema_extra = {
            "example": {
                "capability_code": "max_devices",
                "value_int": 100,
                "reason": "Promoción especial Q4 2024",
                "expires_at": "2024-12-31T23:59:59Z",
            }
        }


class OrganizationCapabilityOut(BaseModel):
    """Override de capability en respuestas."""

    client_id: UUID
    capability_id: UUID
    capability_code: str
    value: Union[int, bool, str, None]
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "client_id": "123e4567-e89b-12d3-a456-426614174000",
                "capability_id": "223e4567-e89b-12d3-a456-426614174000",
                "capability_code": "max_devices",
                "value": 100,
                "reason": "Promoción especial Q4 2024",
                "expires_at": "2024-12-31T23:59:59Z",
            }
        }


class PlanCapabilityOut(BaseModel):
    """Capability de un plan en respuestas."""

    plan_id: UUID
    capability_code: str
    value: Union[int, bool, str, None]

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "123e4567-e89b-12d3-a456-426614174000",
                "capability_code": "max_devices",
                "value": 10,
            }
        }


class ValidateLimitRequest(BaseModel):
    """Request para validar un límite."""

    capability_code: str = Field(..., description="Código de la capability de límite")
    current_count: int = Field(..., ge=0, description="Cantidad actual")

    class Config:
        json_schema_extra = {
            "example": {
                "capability_code": "max_devices",
                "current_count": 8,
            }
        }


class ValidateLimitResponse(BaseModel):
    """Response de validación de límite."""

    can_add: bool = Field(..., description="Si puede agregar uno más")
    current_count: int = Field(..., description="Cantidad actual")
    limit: int = Field(..., description="Límite de la capability")
    remaining: int = Field(..., description="Espacios restantes")

    class Config:
        json_schema_extra = {
            "example": {
                "can_add": True,
                "current_count": 8,
                "limit": 10,
                "remaining": 2,
            }
        }
