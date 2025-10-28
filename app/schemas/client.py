from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.models.client import ClientStatus


class ClientBase(BaseModel):
    name: str
    status: ClientStatus


class ClientOut(ClientBase):
    id: UUID
    active_subscription_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Transportes García",
                "status": "ACTIVE",
                "active_subscription_id": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }
