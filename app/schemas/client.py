from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator, Field
from app.models.client import ClientStatus
from app.utils.validators import validate_password, validate_name


class ClientBase(BaseModel):
    name: str
    status: ClientStatus = ClientStatus.ACTIVE


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
                "status": "PENDING",
                "active_subscription_id": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre del cliente")
    email: EmailStr = Field(..., description="Correo electrónico del cliente")
    password: str = Field(..., min_length=8, description="Contraseña del cliente")

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        """Valida la contraseña usando el validador reutilizable."""
        return validate_password(v)

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        """Valida el nombre usando el validador reutilizable."""
        return validate_name(v)
