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


class UserLogin(BaseModel):
    """Schema para la petición de login."""
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    password: str = Field(..., min_length=1, description="Contraseña del usuario")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "password": "MiPassword123!"
            }
        }


class UserLoginResponse(BaseModel):
    """Schema para la respuesta de login."""
    user: "UserOut"
    access_token: str
    id_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "usuario@example.com",
                    "full_name": "Juan García",
                    "is_master": True,
                },
                "access_token": "eyJraWQiOiJ...",
                "id_token": "eyJraWQiOiJ...",
                "refresh_token": "eyJjdHkiOiJ...",
                "token_type": "Bearer",
                "expires_in": 3600
            }
        }


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


class UserInvite(BaseModel):
    """Schema para invitar un usuario."""
    email: EmailStr = Field(..., description="Correo electrónico del usuario a invitar")
    full_name: str = Field(..., min_length=1, description="Nombre completo del usuario")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "invitado@ejemplo.com",
                "full_name": "Juan Pérez"
            }
        }


class UserInviteResponse(BaseModel):
    """Schema para la respuesta de invitación."""
    detail: str
    expires_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invitación enviada a invitado@ejemplo.com",
                "expires_at": "2025-11-05T23:59:00"
            }
        }


class UserAcceptInvitation(BaseModel):
    """Schema para aceptar una invitación."""
    token: str = Field(..., description="Token de invitación")
    password: str = Field(..., min_length=8, description="Contraseña del usuario")

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        """Valida la contraseña usando el validador reutilizable."""
        return validate_password(v)

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123-def456-ghi789",
                "password": "MiPassword123!"
            }
        }


class UserAcceptInvitationResponse(BaseModel):
    """Schema para la respuesta de aceptación de invitación."""
    detail: str
    user: UserOut

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Usuario creado exitosamente.",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "client_id": "223e4567-e89b-12d3-a456-426614174000",
                    "email": "invitado@ejemplo.com",
                    "full_name": "Juan Pérez",
                    "is_master": False,
                    "email_verified": True,
                    "created_at": "2024-01-10T08:00:00Z",
                    "updated_at": "2024-01-10T08:00:00Z",
                }
            }
        }


class ForgotPasswordRequest(BaseModel):
    """Schema para solicitar recuperación de contraseña."""
    email: EmailStr = Field(..., description="Correo electrónico del usuario")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com"
            }
        }


class ForgotPasswordResponse(BaseModel):
    """Schema para la respuesta de solicitud de recuperación de contraseña."""
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Se ha enviado un código de verificación al correo registrado."
            }
        }


class ResetPasswordRequest(BaseModel):
    """Schema para restablecer la contraseña."""
    token: str = Field(..., description="Token de recuperación de contraseña")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña del usuario")

    @field_validator("new_password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        """Valida la contraseña usando el validador reutilizable."""
        return validate_password(v)

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123-def456-ghi789",
                "new_password": "NuevaPassword123!"
            }
        }


class ResetPasswordResponse(BaseModel):
    """Schema para la respuesta de restablecimiento de contraseña."""
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
            }
        }
