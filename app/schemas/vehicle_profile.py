from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VehicleProfileBase(BaseModel):
    """Schema base para VehicleProfile"""

    plate: Optional[str] = Field(None, max_length=20, description="Placa del vehículo")
    vin: Optional[str] = Field(None, max_length=50, description="VIN del vehículo")
    fuel_type: Optional[str] = Field(
        None, max_length=50, description="Tipo de combustible"
    )
    passengers: Optional[int] = Field(
        None, ge=1, le=100, description="Capacidad de pasajeros"
    )


class VehicleProfileCreate(VehicleProfileBase):
    """Schema para crear un perfil de vehículo"""

    pass


class VehicleProfileUpdate(BaseModel):
    """Schema para actualizar un perfil de vehículo"""

    plate: Optional[str] = Field(None, max_length=20)
    vin: Optional[str] = Field(None, max_length=50)
    fuel_type: Optional[str] = Field(None, max_length=50)
    passengers: Optional[int] = Field(None, ge=1, le=100)


class VehicleProfileOut(VehicleProfileBase):
    """Schema de salida para VehicleProfile"""

    unit_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "unit_id": "def45678-e89b-12d3-a456-426614174000",
                "plate": "ABC-123",
                "vin": "1FDUF3GT5GED12345",
                "fuel_type": "Diesel",
                "passengers": 5,
                "created_at": "2025-11-15T10:30:00Z",
                "updated_at": "2025-11-15T10:30:00Z",
            }
        }
