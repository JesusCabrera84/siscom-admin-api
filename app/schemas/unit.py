from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UnitBase(BaseModel):
    """Schema base para Unit"""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Nombre de la unidad"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Descripción opcional"
    )


class UnitCreate(UnitBase):
    """Schema para crear una nueva unidad"""

    pass


class UnitUpdate(BaseModel):
    """Schema para actualizar una unidad"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)


class UnitOut(UnitBase):
    """Schema de salida para unidad"""

    id: UUID
    client_id: UUID
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abc12345-e89b-12d3-a456-426614174000",
                "client_id": "def45678-e89b-12d3-a456-426614174000",
                "name": "Camión #45",
                "description": "Camión de reparto zona norte",
                "deleted_at": None,
            }
        }


class UnitWithDevice(UnitBase):
    """Schema de unidad con información del dispositivo asignado"""

    id: UUID
    client_id: UUID
    deleted_at: Optional[datetime] = None
    # Información del dispositivo asignado (null si no tiene)
    device_id: Optional[str] = None
    device_brand: Optional[str] = None
    device_model: Optional[str] = None
    assigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abc12345-e89b-12d3-a456-426614174000",
                "client_id": "def45678-e89b-12d3-a456-426614174000",
                "name": "Camión #45",
                "description": "Camión de reparto zona norte",
                "deleted_at": None,
                "device_id": "864537040123456",
                "device_brand": "Suntech",
                "device_model": "ST300",
                "assigned_at": "2025-11-15T10:30:00Z",
            }
        }


class UnitDetail(UnitOut):
    """Schema detallado de unidad con dispositivos asignados"""

    active_devices_count: int = Field(
        default=0, description="Número de dispositivos activos"
    )
    total_devices_count: int = Field(
        default=0, description="Total de dispositivos (histórico)"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abc12345-e89b-12d3-a456-426614174000",
                "client_id": "def45678-e89b-12d3-a456-426614174000",
                "name": "Camión #45",
                "description": "Camión de reparto zona norte",
                "deleted_at": None,
                "active_devices_count": 2,
                "total_devices_count": 3,
            }
        }
