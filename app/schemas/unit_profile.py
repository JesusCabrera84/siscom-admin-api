from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.vehicle_profile import VehicleProfileOut


class UnitProfileBase(BaseModel):
    """Schema base para UnitProfile"""

    unit_type: str = Field(
        ..., min_length=1, max_length=100, description="Tipo de unidad"
    )
    icon_type: Optional[str] = Field(None, max_length=100, description="Tipo de ícono")
    description: Optional[str] = Field(None, max_length=500, description="Descripción")
    brand: Optional[str] = Field(None, max_length=100, description="Marca")
    model: Optional[str] = Field(None, max_length=100, description="Modelo")
    serial: Optional[str] = Field(None, max_length=100, description="Número de serie")
    color: Optional[str] = Field(None, max_length=50, description="Color")
    year: Optional[int] = Field(
        None, ge=1900, le=2100, description="Año de fabricación"
    )


class UnitProfileUpdate(BaseModel):
    """
    Schema para actualizar un perfil de unidad.

    Soporta actualización unificada de unit_profile y vehicle_profile.
    Si se envían campos de vehículo (plate, vin, fuel_type, passengers)
    y la unidad es de tipo 'vehicle', se hace upsert automático del vehicle_profile.
    """

    # Campos de unit_profile (universales)
    icon_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=50)
    year: Optional[int] = Field(None, ge=1900, le=2100)

    # Campos de vehicle_profile (solo si unit_type = "vehicle")
    plate: Optional[str] = Field(None, max_length=20)
    vin: Optional[str] = Field(None, max_length=50)
    fuel_type: Optional[str] = Field(None, max_length=50)
    passengers: Optional[int] = Field(None, ge=1, le=100)


class UnitProfileOut(UnitProfileBase):
    """Schema de salida para UnitProfile"""

    profile_id: UUID
    unit_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "profile_id": "abc12345-e89b-12d3-a456-426614174000",
                "unit_id": "def45678-e89b-12d3-a456-426614174000",
                "unit_type": "vehicle",
                "icon_type": "truck",
                "description": "Camión de carga pesada",
                "brand": "Ford",
                "model": "F-350",
                "serial": "1FDUF3GT5GED12345",
                "color": "Rojo",
                "year": 2020,
                "created_at": "2025-11-15T10:30:00Z",
                "updated_at": "2025-11-15T10:30:00Z",
            }
        }


class UnitProfileComplete(BaseModel):
    """Schema completo que combina unit_profile y vehicle_profile"""

    unit_id: UUID
    unit_type: str
    icon_type: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    year: Optional[int] = None
    vehicle: Optional[VehicleProfileOut] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "unit_id": "def45678-e89b-12d3-a456-426614174000",
                "unit_type": "vehicle",
                "icon_type": "truck",
                "description": "Camión de carga pesada",
                "brand": "Ford",
                "model": "F-350",
                "color": "Rojo",
                "year": 2020,
                "vehicle": {
                    "unit_id": "def45678-e89b-12d3-a456-426614174000",
                    "plate": "ABC-123",
                    "vin": "1FDUF3GT5GED12345",
                    "fuel_type": "Diesel",
                    "passengers": 5,
                    "created_at": "2025-11-15T10:30:00Z",
                    "updated_at": "2025-11-15T10:30:00Z",
                },
            }
        }
