from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GeofenceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    config: Optional[dict[str, Any]] = None


class GeofenceCreate(GeofenceBase):
    h3_indexes: list[int] = Field(default_factory=list)


class GeofenceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    h3_indexes: Optional[list[int]] = None


class GeofenceOut(GeofenceBase):
    id: UUID
    organization_id: UUID
    created_by: UUID
    h3_indexes: list[int] = Field(default_factory=list)
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GeofenceDeleteOut(BaseModel):
    message: str
    geofence_id: UUID
    is_active: bool
