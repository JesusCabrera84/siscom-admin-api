from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.command import Command
from app.models.device import Device
from app.schemas.command import (
    CommandCreate,
    CommandListResponse,
    CommandOut,
    CommandResponse,
)

router = APIRouter()


@router.post("", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
def create_command(
    command_in: CommandCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Crea un nuevo comando para enviar a un dispositivo.

    **Parámetros:**
    - `command`: El comando a enviar al dispositivo
    - `media`: Medio de comunicación (sms, tcp, etc.)
    - `device_id`: ID del dispositivo destino
    - `template_id`: (Opcional) ID del template de comando
    - `metadata`: (Opcional) Datos adicionales del comando

    **Retorna:**
    - `command_id`: UUID del comando creado
    - `status`: Estado inicial del comando ('pending')
    """
    # Verificar que el dispositivo existe
    device = db.query(Device).filter(Device.device_id == command_in.device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    # Crear el comando
    command = Command(
        template_id=command_in.template_id,
        command=command_in.command,
        media=command_in.media,
        request_user_id=user_id,
        device_id=command_in.device_id,
        command_metadata=command_in.command_metadata,
        status="pending",
    )

    db.add(command)
    db.commit()
    db.refresh(command)

    return CommandResponse(
        command_id=command.command_id,
        status=command.status,
    )


@router.get("/device/{device_id}", response_model=CommandListResponse)
def get_commands_by_device(
    device_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    status_filter: Optional[str] = Query(
        None, description="Filtrar por estado (pending, sent, delivered, failed)"
    ),
    limit: int = Query(50, ge=1, le=500, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
):
    """
    Obtiene todos los comandos enviados a un dispositivo específico.

    **Parámetros:**
    - `device_id`: ID del dispositivo
    - `status_filter`: (Opcional) Filtrar por estado
    - `limit`: Límite de resultados (default: 50, max: 500)
    - `offset`: Offset para paginación

    **Retorna:**
    - Lista de comandos con información completa
    - Total de comandos encontrados
    """
    # Verificar que el dispositivo existe
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    # Construir query base
    query = db.query(Command).filter(Command.device_id == device_id)

    # Aplicar filtro de estado si se proporciona
    if status_filter:
        if status_filter not in ["pending", "sent", "delivered", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estado inválido. Valores válidos: pending, sent, delivered, failed",
            )
        query = query.filter(Command.status == status_filter)

    # Contar total
    total = query.count()

    # Obtener comandos con paginación
    commands = (
        query.order_by(Command.requested_at.desc()).offset(offset).limit(limit).all()
    )

    # Construir respuesta
    commands_out = [
        CommandOut(
            command_id=cmd.command_id,
            template_id=cmd.template_id,
            command=cmd.command,
            media=cmd.media,
            request_user_id=cmd.request_user_id,
            device_id=cmd.device_id,
            requested_at=cmd.requested_at,
            updated_at=cmd.updated_at,
            status=cmd.status,
            command_metadata=cmd.command_metadata,
        )
        for cmd in commands
    ]

    return CommandListResponse(commands=commands_out, total=total)


@router.get("/{command_id}", response_model=CommandOut)
def get_command(
    command_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Obtiene el detalle de un comando específico por su ID.

    **Parámetros:**
    - `command_id`: UUID del comando

    **Retorna:**
    - Información completa del comando
    """
    command = db.query(Command).filter(Command.command_id == command_id).first()

    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comando no encontrado",
        )

    return CommandOut(
        command_id=command.command_id,
        template_id=command.template_id,
        command=command.command,
        media=command.media,
        request_user_id=command.request_user_id,
        device_id=command.device_id,
        requested_at=command.requested_at,
        updated_at=command.updated_at,
        status=command.status,
        command_metadata=command.command_metadata,
    )
