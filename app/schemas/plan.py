"""
Schemas para Planes.

Los planes son INFORMATIVOS - definen precios y capabilities disponibles.
Las capabilities específicas se configuran en plan_capabilities.

IMPORTANTE: Los planes NO gobiernan la lógica del sistema.
La lógica está en:
- Suscripciones: determinan qué plan tiene cada organización
- Capabilities: determinan qué puede hacer cada organización
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BillingCycle(str, Enum):
    """Ciclos de facturación disponibles."""
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class PlanPricing(BaseModel):
    """Precios de un plan por ciclo de facturación."""
    monthly: Decimal = Field(..., description="Precio mensual")
    yearly: Decimal = Field(..., description="Precio anual")
    yearly_savings_percent: int = Field(
        default=0,
        description="Porcentaje de ahorro al pagar anualmente"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "monthly": "599.00",
                "yearly": "5990.00",
                "yearly_savings_percent": 17
            }
        }


class PlanBase(BaseModel):
    """Base para un plan."""
    name: str = Field(..., description="Nombre del plan")
    code: str = Field(..., description="Código único del plan (ej: basic, pro, enterprise)")
    description: Optional[str] = Field(None, description="Descripción del plan")


class PlanOut(PlanBase):
    """Plan en respuestas (lectura básica)."""
    id: UUID
    price_monthly: Decimal = Field(..., description="Precio mensual")
    price_yearly: Decimal = Field(..., description="Precio anual")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Plan Profesional",
                "code": "pro",
                "description": "Plan profesional para flotas medianas",
                "price_monthly": "599.00",
                "price_yearly": "5990.00",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class PlanDetailOut(PlanBase):
    """
    Plan con detalle completo para frontend.

    Incluye:
    - Precios estructurados
    - Ciclos de facturación disponibles
    - Capabilities del plan
    - Features destacados (para UI)
    """
    id: UUID
    pricing: PlanPricing = Field(..., description="Estructura de precios")
    billing_cycles: list[BillingCycle] = Field(
        default=[BillingCycle.MONTHLY, BillingCycle.YEARLY],
        description="Ciclos de facturación disponibles para este plan"
    )
    capabilities: dict[str, Any] = Field(
        default_factory=dict,
        description="Capabilities incluidas en el plan (límites y features)"
    )
    highlighted_features: list[str] = Field(
        default_factory=list,
        description="Features destacados para mostrar en UI"
    )
    is_popular: bool = Field(
        default=False,
        description="Indica si es el plan más popular/recomendado"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Plan Profesional",
                "code": "pro",
                "description": "Plan profesional para flotas medianas",
                "pricing": {
                    "monthly": "599.00",
                    "yearly": "5990.00",
                    "yearly_savings_percent": 17
                },
                "billing_cycles": ["MONTHLY", "YEARLY"],
                "capabilities": {
                    "max_devices": 50,
                    "max_geofences": 100,
                    "max_users": 10,
                    "history_days": 90,
                    "ai_features": True,
                    "analytics_tools": True,
                },
                "highlighted_features": [
                    "Hasta 50 dispositivos",
                    "100 geocercas",
                    "90 días de historial",
                    "Funciones de IA incluidas"
                ],
                "is_popular": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


# Alias para compatibilidad
PlanWithCapabilitiesOut = PlanDetailOut


class PlansListOut(BaseModel):
    """Lista de planes disponibles."""
    plans: list[PlanDetailOut]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "plans": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Plan Básico",
                        "code": "basic",
                        "description": "Ideal para flotas pequeñas",
                        "pricing": {
                            "monthly": "299.00",
                            "yearly": "2990.00",
                            "yearly_savings_percent": 17
                        },
                        "billing_cycles": ["MONTHLY", "YEARLY"],
                        "capabilities": {
                            "max_devices": 10,
                            "max_geofences": 20,
                            "history_days": 30
                        },
                        "highlighted_features": [
                            "Hasta 10 dispositivos",
                            "20 geocercas"
                        ],
                        "is_popular": False
                    },
                    {
                        "id": "223e4567-e89b-12d3-a456-426614174000",
                        "name": "Plan Profesional",
                        "code": "pro",
                        "description": "Para flotas medianas con necesidades avanzadas",
                        "pricing": {
                            "monthly": "599.00",
                            "yearly": "5990.00",
                            "yearly_savings_percent": 17
                        },
                        "billing_cycles": ["MONTHLY", "YEARLY"],
                        "capabilities": {
                            "max_devices": 50,
                            "ai_features": True
                        },
                        "highlighted_features": [
                            "Hasta 50 dispositivos",
                            "Funciones de IA"
                        ],
                        "is_popular": True
                    },
                ],
                "total": 2,
            }
        }
