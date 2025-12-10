import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import AuthResult, get_auth_cognito_or_paseto
from app.db.session import get_db
from app.models.command import Command
from app.models.device import Device
from app.models.unified_sim_profile import UnifiedSimProfile
from app.schemas.command import (
    CommandCreate,
    CommandListResponse,
    CommandOut,
    CommandResponse,
)
from app.services.kore import KoreAuthError, KoreSmsError, kore_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependencia para autenticación dual (Cognito o PASETO)
get_auth_for_commands = get_auth_cognito_or_paseto(
    required_service="gac",
    required_role="NEXUS_ADMIN",
)


@router.post("", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
async def create_command(
    command_in: CommandCreate,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_commands),
):
    """
    Crea un nuevo comando para enviar a un dispositivo.

    **Autenticación:**
    - Token de Cognito: Usuario autenticado del sistema
    - Token PASETO: Requiere service="gac" y role="NEXUS_ADMIN"

    **Parámetros:**
    - `command`: El comando a enviar al dispositivo
    - `media`: Medio de comunicación (sms, tcp, etc.)
    - `device_id`: ID del dispositivo destino
    - `template_id`: (Opcional) ID del template de comando
    - `command_metadata`: (Opcional) Datos adicionales del comando

    **Comportamiento:**
    - Si el dispositivo tiene una SIM con kore_sim_id configurado,
      el comando se enviará automáticamente vía KORE SMS.

    **Retorna:**
    - `command_id`: UUID del comando creado
    - `status`: Estado del comando ('pending', 'sent', o 'failed')
    """
    # Verificar que el dispositivo existe
    device = db.query(Device).filter(Device.device_id == command_in.device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    # Obtener email según el tipo de autenticación
    # Para Cognito: obtener email del payload del token
    # Para PASETO: obtener email del payload
    request_user_email: str
    request_user_id = None

    if auth.auth_type == "cognito":
        # Obtener email del token Cognito
        request_user_email = auth.payload.get("email")
        request_user_id = auth.user_id
        if not request_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token Cognito inválido: falta el campo 'email'",
            )
    else:  # paseto
        request_user_email = auth.payload.get("email")
        if not request_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token PASETO inválido: falta el campo 'email'",
            )

    # Crear el comando
    command = Command(
        template_id=command_in.template_id,
        command=command_in.command,
        media=command_in.media,
        request_user_id=request_user_id,
        request_user_email=request_user_email,
        device_id=command_in.device_id,
        command_metadata=command_in.command_metadata,
        status="pending",
    )

    db.add(command)
    db.commit()
    db.refresh(command)

    # Intentar enviar el comando vía KORE si está configurado
    kore_error = None

    if kore_service.is_configured():
        # Consultar la vista unified_sim_profiles para obtener kore_sim_id
        sim_profile = (
            db.query(UnifiedSimProfile)
            .filter(UnifiedSimProfile.device_id == command_in.device_id)
            .first()
        )

        if sim_profile and sim_profile.kore_sim_id:
            logger.info(
                f"[COMMANDS] Enviando comando vía KORE para device_id={command_in.device_id}, "
                f"kore_sim_id={sim_profile.kore_sim_id}"
            )

            try:
                # Autenticar con KORE
                auth_response = await kore_service.authenticate()

                # Enviar el comando SMS
                sms_response = await kore_service.send_sms_command(
                    kore_sim_id=sim_profile.kore_sim_id,
                    payload=command_in.command,
                    access_token=auth_response.access_token,
                )

                if sms_response.success:
                    # Actualizar estado del comando a 'sent'
                    command.status = "sent"
                    # Guardar metadata de la respuesta de KORE
                    if command.command_metadata is None:
                        command.command_metadata = {}
                    command.command_metadata["kore_response"] = (
                        sms_response.response_data
                    )
                    command.command_metadata["kore_sim_id"] = sim_profile.kore_sim_id
                    logger.info(
                        f"[COMMANDS] Comando enviado exitosamente vía KORE: "
                        f"command_id={command.command_id}"
                    )
                else:
                    # Error al enviar, mantener como pending o marcar como failed
                    kore_error = sms_response.message
                    logger.warning(
                        f"[COMMANDS] Error KORE al enviar comando: {kore_error}"
                    )

            except KoreAuthError as e:
                kore_error = f"Error de autenticación KORE: {str(e)}"
                logger.error(f"[COMMANDS] {kore_error}")

            except KoreSmsError as e:
                kore_error = f"Error SMS KORE: {str(e)}"
                logger.error(f"[COMMANDS] {kore_error}")

            except Exception as e:
                kore_error = f"Error inesperado KORE: {str(e)}"
                logger.exception(f"[COMMANDS] {kore_error}")

            # Guardar error en metadata si hubo
            if kore_error:
                if command.command_metadata is None:
                    command.command_metadata = {}
                command.command_metadata["kore_error"] = kore_error

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
    auth: AuthResult = Depends(get_auth_for_commands),
    status_filter: Optional[str] = Query(
        None, description="Filtrar por estado (pending, sent, delivered, failed)"
    ),
    limit: int = Query(50, ge=1, le=500, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
):
    """
    Obtiene todos los comandos enviados a un dispositivo específico.

    **Autenticación:**
    - Token de Cognito: Usuario autenticado del sistema
    - Token PASETO: Requiere service="gac" y role="NEXUS_ADMIN"

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
            request_user_email=cmd.request_user_email,
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
    auth: AuthResult = Depends(get_auth_for_commands),
):
    """
    Obtiene el detalle de un comando específico por su ID.

    **Autenticación:**
    - Token de Cognito: Usuario autenticado del sistema
    - Token PASETO: Requiere service="gac" y role="NEXUS_ADMIN"

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
        request_user_email=command.request_user_email,
        device_id=command.device_id,
        requested_at=command.requested_at,
        updated_at=command.updated_at,
        status=command.status,
        command_metadata=command.command_metadata,
    )
