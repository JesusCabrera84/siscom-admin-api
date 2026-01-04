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
        default=0, description="Porcentaje de ahorro al pagar anualmente"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "monthly": "599.00",
                "yearly": "5990.00",
                "yearly_savings_percent": 17,
            }
        }


class PlanBase(BaseModel):
    """Base para un plan."""

    name: str = Field(..., description="Nombre del plan")
    code: str = Field(
        ..., description="Código único del plan (ej: basic, pro, enterprise)"
    )
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
        description="Ciclos de facturación disponibles para este plan",
    )
    capabilities: dict[str, Any] = Field(
        default_factory=dict,
        description="Capabilities incluidas en el plan (límites y features)",
    )
    highlighted_features: list[str] = Field(
        default_factory=list, description="Features destacados para mostrar en UI"
    )
    is_popular: bool = Field(
        default=False, description="Indica si es el plan más popular/recomendado"
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
                    "yearly_savings_percent": 17,
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
                    "Funciones de IA incluidas",
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
                            "yearly_savings_percent": 17,
                        },
                        "billing_cycles": ["MONTHLY", "YEARLY"],
                        "capabilities": {
                            "max_devices": 10,
                            "max_geofences": 20,
                            "history_days": 30,
                        },
                        "highlighted_features": [
                            "Hasta 10 dispositivos",
                            "20 geocercas",
                        ],
                        "is_popular": False,
                    },
                    {
                        "id": "223e4567-e89b-12d3-a456-426614174000",
                        "name": "Plan Profesional",
                        "code": "pro",
                        "description": "Para flotas medianas con necesidades avanzadas",
                        "pricing": {
                            "monthly": "599.00",
                            "yearly": "5990.00",
                            "yearly_savings_percent": 17,
                        },
                        "billing_cycles": ["MONTHLY", "YEARLY"],
                        "capabilities": {"max_devices": 50, "ai_features": True},
                        "highlighted_features": [
                            "Hasta 50 dispositivos",
                            "Funciones de IA",
                        ],
                        "is_popular": True,
                    },
                ],
                "total": 2,
            }
        }


# =============================================================================
# Schemas para CRUD de Plans (Admin)
# =============================================================================


class PlanCapabilityInput(BaseModel):
    """Capability a incluir en un plan."""

    capability_code: str = Field(..., description="Código de la capability")
    value_int: Optional[int] = Field(None, description="Valor entero")
    value_bool: Optional[bool] = Field(None, description="Valor booleano")
    value_text: Optional[str] = Field(None, description="Valor texto")

    class Config:
        json_schema_extra = {
            "example": {
                "capability_code": "max_devices",
                "value_int": 50,
            }
        }


class PlanCreate(BaseModel):
    """
    Schema para crear un plan completo (endpoint compuesto).

    Crea el plan con toda su información en una sola operación:
    - Datos comerciales (nombre, código, descripción)
    - Precios
    - Estado (activo/inactivo)
    - Capabilities base
    - Productos asociados
    """

    name: str = Field(..., min_length=1, max_length=255, description="Nombre del plan")
    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
        description="Código único del plan (minúsculas, números, guión bajo)",
    )
    description: Optional[str] = Field(None, description="Descripción del plan")
    price_monthly: Decimal = Field(
        ..., ge=0, description="Precio mensual en la moneda base"
    )
    price_yearly: Decimal = Field(
        ..., ge=0, description="Precio anual en la moneda base"
    )
    is_active: bool = Field(True, description="Si el plan está activo")
    capabilities: list[PlanCapabilityInput] = Field(
        default_factory=list, description="Capabilities incluidas en el plan"
    )
    product_codes: list[str] = Field(
        default_factory=list, description="Códigos de productos incluidos en el plan"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Plan Profesional",
                "code": "pro",
                "description": "Plan profesional para flotas medianas",
                "price_monthly": "599.00",
                "price_yearly": "5990.00",
                "is_active": True,
                "capabilities": [
                    {"capability_code": "max_devices", "value_int": 50},
                    {"capability_code": "max_users", "value_int": 10},
                    {"capability_code": "ai_features", "value_bool": True},
                ],
                "product_codes": ["gps_tracker", "dashcam"],
            }
        }


class PlanUpdate(BaseModel):
    """
    Schema para actualizar un plan de forma completa (endpoint compuesto).

    Soporta edición parcial: solo se actualizan los campos enviados.
    Las capabilities y productos se reemplazan completamente si se envían.
    """

    name: Optional[str] = Field(None, description="Nombre del plan")
    description: Optional[str] = Field(None, description="Descripción del plan")
    price_monthly: Optional[Decimal] = Field(None, ge=0, description="Precio mensual")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Precio anual")
    is_active: Optional[bool] = Field(None, description="Si el plan está activo")
    capabilities: Optional[list[PlanCapabilityInput]] = Field(
        None,
        description="Capabilities del plan (reemplaza todas las existentes si se envía)",
    )
    product_codes: Optional[list[str]] = Field(
        None,
        description="Códigos de productos incluidos (reemplaza todos si se envía)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Plan profesional actualizado",
                "price_monthly": "649.00",
                "price_yearly": "6490.00",
                "is_active": True,
                "capabilities": [
                    {"capability_code": "max_devices", "value_int": 75},
                    {"capability_code": "ai_features", "value_bool": True},
                ],
                "product_codes": ["gps_tracker", "dashcam"],
            }
        }


class PlanCapabilityAdminOut(BaseModel):
    """Capability de un plan en respuestas administrativas."""

    capability_id: UUID
    capability_code: str
    value: Any
    value_type: str


class PlanProductAdminOut(BaseModel):
    """Producto de un plan en respuestas administrativas."""

    product_id: UUID
    code: str
    name: str


class PlanAdminOut(BaseModel):
    """
    Plan con información administrativa completa.

    Usado para la UI de gestión de planes en GAC.
    """

    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    price_monthly: Decimal
    price_yearly: Decimal
    is_active: bool = True
    capabilities: list[PlanCapabilityAdminOut] = Field(
        default_factory=list, description="Capabilities del plan"
    )
    products: list[PlanProductAdminOut] = Field(
        default_factory=list, description="Productos del plan"
    )
    subscriptions_count: int = Field(0, description="Número de suscripciones activas")
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
                "is_active": True,
                "capabilities": [
                    {
                        "capability_id": "cap-uuid",
                        "capability_code": "max_devices",
                        "value": 50,
                        "value_type": "int",
                    }
                ],
                "products": [
                    {
                        "product_id": "prod-uuid",
                        "code": "gps_tracker",
                        "name": "GPS Tracker",
                    }
                ],
                "subscriptions_count": 15,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


# =============================================================================
# Schemas para Products
# =============================================================================


class ProductCreate(BaseModel):
    """Schema para crear un producto."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
        description="Código único del producto",
    )
    name: str = Field(
        ..., min_length=1, max_length=255, description="Nombre del producto"
    )
    description: Optional[str] = Field(None, description="Descripción del producto")
    is_active: bool = Field(True, description="Si el producto está activo")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "gps_tracker",
                "name": "GPS Tracker Premium",
                "description": "Dispositivo GPS con rastreo en tiempo real",
                "is_active": True,
            }
        }


class ProductUpdate(BaseModel):
    """Schema para actualizar un producto."""

    name: Optional[str] = Field(None, description="Nombre del producto")
    description: Optional[str] = Field(None, description="Descripción del producto")
    is_active: Optional[bool] = Field(None, description="Si el producto está activo")

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Dispositivo GPS mejorado con rastreo avanzado",
                "is_active": True,
            }
        }


class ProductOut(BaseModel):
    """Producto en respuestas."""

    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "code": "gps_tracker",
                "name": "GPS Tracker Premium",
                "description": "Dispositivo GPS con rastreo en tiempo real",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
            }
        }


class ProductsListOut(BaseModel):
    """Lista de productos."""

    products: list[ProductOut]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "code": "gps_tracker",
                        "name": "GPS Tracker Premium",
                        "description": "Dispositivo GPS con rastreo en tiempo real",
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z",
                    }
                ],
                "total": 1,
            }
        }


# =============================================================================
# Schemas para Plan Capabilities
# =============================================================================


class PlanCapabilityOut(BaseModel):
    """Capability de un plan en respuestas."""

    plan_id: UUID
    capability_id: UUID
    capability_code: str
    value: Any
    value_type: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanCapabilitiesListOut(BaseModel):
    """Lista de capabilities de un plan."""

    plan_id: UUID
    plan_code: str
    capabilities: list[PlanCapabilityOut]
    total: int


# =============================================================================
# Schemas para Plan Products
# =============================================================================


class PlanProductsListOut(BaseModel):
    """Lista de productos de un plan."""

    plan_id: UUID
    plan_code: str
    products: list[ProductOut]
    total: int
