from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CommandCreate(BaseModel):
    """Schema para crear un nuevo comando."""

    template_id: Optional[UUID] = Field(
        default=None, description="ID del template de comando (opcional)"
    )
    command: str = Field(..., description="Comando a enviar al dispositivo")
    media: str = Field(..., description="Medio de comunicación (sms, tcp, etc.)")
    device_id: str = Field(..., description="ID del dispositivo destino")
    command_metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Metadata adicional del comando"
    )


class CommandResponse(BaseModel):
    """Schema de respuesta al crear un comando."""

    command_id: UUID
    status: str


class CommandOut(BaseModel):
    """Schema completo de un comando."""

    command_id: UUID
    template_id: Optional[UUID] = None
    command: str
    media: str
    request_user_id: Optional[UUID] = None
    request_user_email: str
    device_id: str
    requested_at: datetime
    updated_at: datetime
    status: str
    command_metadata: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class CommandListResponse(BaseModel):
    """Schema para lista de comandos."""

    commands: list[CommandOut]
    total: int
