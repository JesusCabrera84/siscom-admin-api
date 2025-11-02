from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator, Field
from app.utils.validators import validate_password, validate_name


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_master: bool = False


class UserCreate(UserBase):
    client_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, description="Nombre del usuario")
    password: str = Field(..., min_length=8, description="Contraseña del usuario")

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


class UserOut(UserBase):
    id: UUID
    client_id: UUID
    cognito_sub: Optional[str] = None
    email_verified: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "client_id": "223e4567-e89b-12d3-a456-426614174000",
                "cognito_sub": "us-east-1:12345678-1234-1234-1234-123456789012",
                "email": "usuario@example.com",
                "full_name": "Juan García",
                "is_master": True,
                "email_verified": True,
                "last_login_at": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-10T08:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }
