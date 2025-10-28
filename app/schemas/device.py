from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class DeviceBase(BaseModel):
    imei: str = Field(..., min_length=15, max_length=17)
    brand: Optional[str] = None
    model: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceOut(DeviceBase):
    id: UUID
    client_id: UUID
    active: bool
    installed_in_unit_id: Optional[UUID] = None
    last_comm_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "client_id": "223e4567-e89b-12d3-a456-426614174000",
                "imei": "123456789012345",
                "brand": "Queclink",
                "model": "GV300",
                "active": True,
                "installed_in_unit_id": "323e4567-e89b-12d3-a456-426614174000",
                "last_comm_at": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-10T08:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class UnitBase(BaseModel):
    name: str
    plate: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class UnitCreate(UnitBase):
    pass


class UnitOut(UnitBase):
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174000",
                "client_id": "223e4567-e89b-12d3-a456-426614174000",
                "name": "Camión 01",
                "plate": "ABC-123-XY",
                "type": "Camión de carga",
                "description": "Camión para entregas locales",
                "created_at": "2024-01-10T08:00:00Z",
                "updated_at": "2024-01-10T08:00:00Z",
            }
        }
