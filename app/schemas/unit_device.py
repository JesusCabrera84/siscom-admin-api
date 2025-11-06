from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UnitDeviceCreate(BaseModel):
    """Schema para asignar un dispositivo a una unidad"""

    unit_id: UUID = Field(..., description="ID de la unidad")
    device_id: str = Field(
        ..., min_length=10, max_length=50, description="ID del dispositivo"
    )


class UnitDeviceAssign(BaseModel):
    """Schema para asignar un dispositivo a una unidad (endpoint jerárquico)"""

    device_id: str = Field(
        ..., min_length=10, max_length=50, description="ID del dispositivo"
    )

    class Config:
        json_schema_extra = {"example": {"device_id": "864537040123456"}}


class UnitDeviceOut(BaseModel):
    """Schema de salida para asignación unit-device"""

    id: UUID
    unit_id: UUID
    device_id: str
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abc12345-e89b-12d3-a456-426614174000",
                "unit_id": "def45678-e89b-12d3-a456-426614174000",
                "device_id": "864537040123456",
                "assigned_at": "2025-11-03T08:00:00Z",
                "unassigned_at": None,
            }
        }


class UnitDeviceDetail(BaseModel):
    """Schema detallado de asignación con información de unidad y dispositivo"""

    id: UUID
    unit_id: UUID
    device_id: str
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None

    # Información adicional
    unit_name: Optional[str] = None
    device_brand: Optional[str] = None
    device_model: Optional[str] = None
    device_status: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abc12345-e89b-12d3-a456-426614174000",
                "unit_id": "def45678-e89b-12d3-a456-426614174000",
                "device_id": "864537040123456",
                "assigned_at": "2025-11-03T08:00:00Z",
                "unassigned_at": None,
                "unit_name": "Camión #45",
                "device_brand": "Suntech",
                "device_model": "ST300",
                "device_status": "asignado",
            }
        }
