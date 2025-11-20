"""
Schemas para el módulo de contacto.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.utils.validators import sanitize_contact_field, sanitize_html, validate_phone


class ContactMessageCreate(BaseModel):
    """Schema para crear un mensaje de contacto."""

    nombre: str
    correo_electronico: Optional[EmailStr] = None
    telefono: Optional[str] = None
    mensaje: str

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """Valida y sanitiza el nombre."""
        if not v or not v.strip():
            raise ValueError("El nombre es requerido")
        # Sanitizar y validar longitud máxima de 200 caracteres
        return sanitize_contact_field(v, "nombre", max_length=200)

    @field_validator("mensaje")
    @classmethod
    def validate_mensaje(cls, v: str) -> str:
        """Valida y sanitiza el mensaje."""
        if not v or not v.strip():
            raise ValueError("El mensaje es requerido")
        # Sanitizar mensaje con longitud máxima de 5000 caracteres
        return sanitize_html(v, max_length=5000)

    @field_validator("telefono")
    @classmethod
    def validate_telefono(cls, v: Optional[str]) -> Optional[str]:
        """Valida, limpia y sanitiza el teléfono."""
        if not v:
            return v
        # Validar formato y sanitizar
        return validate_phone(v)

    def model_post_init(self, __context) -> None:
        """Valida que al menos correo_electronico o telefono estén presentes."""
        if not self.correo_electronico and not self.telefono:
            raise ValueError(
                "Debe proporcionar al menos un correo electrónico o un teléfono"
            )


class ContactMessageResponse(BaseModel):
    """Schema para la respuesta del envío de mensaje de contacto."""

    success: bool
    message: str
