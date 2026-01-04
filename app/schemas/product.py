"""
Schemas para Productos.

Los productos representan items que pueden incluirse en planes.
Ejemplos: GPS Tracker, Dashcam, Sensor de combustible, etc.

Tabla: products
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    """Base para un producto."""

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


class ProductCreate(ProductBase):
    """Schema para crear un producto."""

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


class ProductOut(ProductBase):
    """Producto en respuestas."""

    id: UUID
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
