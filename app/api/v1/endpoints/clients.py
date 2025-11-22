from datetime import datetime
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_client_id
from app.core.config import settings
from app.db.session import get_db
from app.models.client import Client, ClientStatus
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.models.user import User
from app.schemas.client import ClientCreate, ClientOut
from app.services.notifications import send_verification_email
from app.utils.security import generate_verification_token

router = APIRouter()

# ------------------------------------------
# Cognito client
# ------------------------------------------
cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo cliente con usuario master asociado.
    El proceso completo es:
    1. Validar que no exista el email en users
    2. Validar que no exista el nombre del cliente
    3. Crear registros temporales en client y user (status PENDING)
    4. Enviar correo de verificación (pendiente de implementar)
    5. Usuario confirma por email
    6. Se crea en Cognito y se actualizan los registros
    """

    # 🔍 Verificar que el email no exista en usuarios
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Ya existe un usuario con este correo electrónico."
        )

    # 🔍 Verificar que el nombre del cliente no exista
    existing_name = db.query(Client).filter(Client.name == data.name).first()
    if existing_name:
        raise HTTPException(
            status_code=400, detail="Ya existe un cliente con este nombre."
        )

    # 1️⃣ Crear registro temporal del cliente (status PENDING)
    client = Client(
        name=data.name,
        status=ClientStatus.PENDING,  # Estado temporal hasta verificar email
    )
    db.add(client)
    db.flush()  # Para obtener el id del cliente

    # 2️⃣ Crear usuario master asociado al cliente (sin password_hash, sin cognito_sub)
    user = User(
        client_id=client.id,
        email=data.email,
        full_name=data.name,
        is_master=True,
        email_verified=False,
        # password_hash no se usa, la autenticación es con Cognito
        # cognito_sub se asignará después de la verificación
    )
    db.add(user)
    db.flush()  # Para obtener el id del usuario

    # 3️⃣ Generar token de verificación y guardar la contraseña temporalmente
    verification_token_str = generate_verification_token()
    token = TokenConfirmacion(
        token=verification_token_str,
        user_id=user.id,
        type=TokenType.EMAIL_VERIFICATION,
        password_temp=data.password,  # Guardar contraseña temporalmente para Cognito
    )
    db.add(token)
    db.commit()
    db.refresh(client)
    db.refresh(user)

    # 5️⃣ Enviar correo de verificación
    email_sent = send_verification_email(user.email, verification_token_str)
    if not email_sent:
        print(f"[WARNING] No se pudo enviar el correo de verificación a {user.email}")

    return client


@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verifica el email del usuario mediante el token enviado por correo.

    Flujo:
    1. Buscar token en la tabla tokens_confirmacion
    2. Validar que el token no haya sido usado y no esté expirado
    3. Buscar usuario asociado al token
    4. Crear usuario en Cognito con email_verified=true
    5. Actualizar usuario con cognito_sub y email_verified=true
    6. Actualizar cliente a status ACTIVE
    7. Marcar token como usado
    """

    # 1️⃣ Buscar token en la tabla tokens_confirmacion
    token_record = (
        db.query(TokenConfirmacion)
        .filter(
            TokenConfirmacion.token == token,
            TokenConfirmacion.type == TokenType.EMAIL_VERIFICATION,
        )
        .first()
    )

    if not token_record:
        raise HTTPException(status_code=400, detail="Token de verificación inválido.")

    # 2️⃣ Validar que el token no haya sido usado
    if token_record.used:
        raise HTTPException(status_code=400, detail="Este token ya ha sido utilizado.")

    # 3️⃣ Validar que el token no esté expirado
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token de verificación expirado.")

    # 4️⃣ Buscar usuario asociado al token
    user = db.query(User).filter(User.id == token_record.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if user.email_verified:
        raise HTTPException(status_code=400, detail="Este email ya ha sido verificado.")

    # 2️⃣ Buscar el cliente asociado
    client = db.query(Client).filter(Client.id == user.client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    # 5️⃣ Validar que el token tenga contraseña temporal
    if not token_record.password_temp:
        raise HTTPException(
            status_code=500,
            detail="Token sin contraseña temporal. No se puede completar la verificación.",
        )

    # 6️⃣ Verificar si el usuario ya existe en Cognito
    cognito_sub = None
    user_exists = False

    try:
        # Intentar obtener el usuario de Cognito
        existing_cognito_user = cognito.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID, Username=user.email
        )
        user_exists = True

        # Obtener el cognito_sub del usuario existente
        cognito_sub = next(
            (
                attr["Value"]
                for attr in existing_cognito_user["UserAttributes"]
                if attr["Name"] == "sub"
            ),
            None,
        )

        print(f"[VERIFY EMAIL] Usuario ya existe en Cognito: {user.email}")

    except ClientError as e:
        if e.response["Error"]["Code"] == "UserNotFoundException":
            # Usuario no existe, continuar con la creación
            user_exists = False
        else:
            # Otro error, re-lanzarlo
            raise HTTPException(
                status_code=500,
                detail=f"Error al verificar usuario en Cognito: {e.response['Error'].get('Message', str(e))}",
            )

    try:
        if not user_exists:
            # 7️⃣ Crear usuario en Cognito con email verificado
            cognito_resp = cognito.admin_create_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=user.email,
                UserAttributes=[
                    {"Name": "email", "Value": user.email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "name", "Value": user.full_name or ""},
                ],
                MessageAction="SUPPRESS",  # No enviar correo automático de Cognito
            )

            # Obtener el cognito_sub del usuario creado
            cognito_sub = next(
                (
                    attr["Value"]
                    for attr in cognito_resp["User"]["Attributes"]
                    if attr["Name"] == "sub"
                ),
                None,
            )

            print(f"[VERIFY EMAIL] Usuario creado en Cognito: {user.email}")

        # 8️⃣ Establecer contraseña permanente del usuario (ya sea nuevo o existente)
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user.email,
            Password=token_record.password_temp,
            Permanent=True,  # Contraseña permanente, no temporal
        )

        # 9️⃣ Asegurarse de que el email esté verificado en Cognito
        if user_exists:
            cognito.admin_update_user_attributes(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=user.email,
                UserAttributes=[
                    {"Name": "email_verified", "Value": "true"},
                ],
            )

        if not cognito_sub:
            raise HTTPException(
                status_code=500,
                detail="No se pudo obtener el cognito_sub del usuario",
            )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        raise HTTPException(
            status_code=500,
            detail=f"Error al configurar usuario en Cognito [{error_code}]: {e.response['Error'].get('Message', str(e))}",
        )

    # 9️⃣ Actualizar usuario en la base de datos
    user.cognito_sub = cognito_sub
    user.email_verified = True

    # 🔟 Actualizar cliente a ACTIVE
    client.status = ClientStatus.ACTIVE

    # 1️⃣1️⃣ Marcar token como usado y limpiar contraseña temporal
    token_record.used = True
    token_record.password_temp = None  # Limpiar contraseña por seguridad

    db.commit()

    return {
        "message": "Email verificado exitosamente. Tu cuenta ha sido activada.",
        "email": user.email,
        "client_id": str(client.id),
    }


@router.get("", response_model=ClientOut)
def get_client_info(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene la información del cliente autenticado.
    """
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    return client
