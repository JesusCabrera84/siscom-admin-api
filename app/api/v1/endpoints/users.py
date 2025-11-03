from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from datetime import datetime, timedelta
from app.db.session import get_db
from app.api.deps import get_current_client_id, get_current_user_full
from app.models.user import User
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.schemas.user import (
    UserCreate, 
    UserOut, 
    UserInvite, 
    UserInviteResponse,
    UserAcceptInvitation,
    UserAcceptInvitationResponse
)
from app.core.config import settings
from app.utils.security import generate_verification_token
from botocore.exceptions import ClientError

import boto3

router = APIRouter()


# ------------------------------------------
# Cognito client
# ------------------------------------------
cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)


# ------------------------------------------
# Crear usuario
# ------------------------------------------
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Crea un usuario en AWS Cognito y lo registra en la base de datos.
    """

    # 🔍 Verificar que el usuario no exista en la base de datos
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="El usuario con este correo electrónico ya existe en el sistema.",
        )

    try:
        # 1️⃣ Crear usuario en Cognito
        cognito_resp = cognito.admin_create_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user.email,
            UserAttributes=[
                {"Name": "email", "Value": user.email},
                {"Name": "email_verified", "Value": "true"},  # Marcar email como verificado
                {"Name": "name", "Value": user.name},
            ],
            DesiredDeliveryMediums=["EMAIL"],  # o "SMS"
            MessageAction="SUPPRESS",  # evita que Cognito envíe correo automático
        )

        # 2️⃣ Establecer contraseña proporcionada por el usuario (permanente)
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user.email,
            Password=user.password,
            Permanent=True,  # Esto evita el estado FORCE_CHANGE_PASSWORD
        )

        # 3️⃣ Extraer el cognito_sub del usuario creado
        cognito_sub = next(
            (attr["Value"] for attr in cognito_resp["User"]["Attributes"] if attr["Name"] == "sub"),
            None
        )

        if not cognito_sub:
            raise HTTPException(
                status_code=500,
                detail="No se pudo obtener el cognito_sub del usuario creado"
            )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "UsernameExistsException":
            raise HTTPException(
                status_code=400, detail="El usuario ya existe en Cognito."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error en Cognito [{error_code}]: {e.response['Error'].get('Message', str(e))}"
        )

    # 4️⃣ Guardar usuario en la base de datos
    new_user = User(
        email=user.email,
        full_name=user.name,  # Usamos el campo 'name' recibido
        cognito_sub=cognito_sub,
        is_master=user.is_master,
        client_id=user.client_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/", response_model=List[UserOut])
def list_users(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Lista todos los usuarios del cliente autenticado.
    """
    users = db.query(User).filter(User.client_id == client_id).all()
    return users


@router.get("/me", response_model=UserOut)
def get_current_user_info(
    current_user: User = Depends(get_current_user_full),
):
    """
    Obtiene la información del usuario actualmente autenticado.
    """
    return current_user


@router.post("/invite", response_model=UserInviteResponse, status_code=status.HTTP_201_CREATED)
def invite_user(
    data: UserInvite,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """
    Permite a un usuario maestro invitar a un nuevo usuario.
    
    Flujo:
    1. Verificar que el usuario autenticado sea maestro (is_master=True)
    2. Verificar que el email no esté ya registrado en la tabla users
    3. Generar un token único en tokens_confirmacion
    4. Enviar email con la URL de invitación (TODO)
    5. Responder con confirmación y fecha de expiración
    """
    
    # 1️⃣ Verificar que el usuario autenticado sea maestro
    if not current_user.is_master:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios maestros pueden enviar invitaciones."
        )
    
    # 2️⃣ Verificar que el email no esté ya registrado
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un usuario registrado con el email {data.email}."
        )
    
    # 3️⃣ Verificar que no haya una invitación pendiente para este email
    existing_invitation = (
        db.query(TokenConfirmacion)
        .filter(
            TokenConfirmacion.email == data.email,
            TokenConfirmacion.type == TokenType.INVITATION,
            ~TokenConfirmacion.used,
            TokenConfirmacion.expires_at > datetime.utcnow()
        )
        .first()
    )
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una invitación pendiente para {data.email}."
        )
    
    # 4️⃣ Generar token de invitación
    invitation_token = generate_verification_token()
    expires_at = datetime.utcnow() + timedelta(days=3)
    
    token_record = TokenConfirmacion(
        token=invitation_token,
        client_id=current_user.client_id,
        email=data.email,
        full_name=data.full_name,
        expires_at=expires_at,
        used=False,
        type=TokenType.INVITATION,
        user_id=None  # No hay user_id todavía, se creará al aceptar
    )
    
    db.add(token_record)
    db.commit()
    
    # TODO: 5️⃣ Enviar correo con la URL de invitación
    # URL ejemplo: https://tu-app.com/accept-invitation?token={invitation_token}
    # await send_invitation_email(data.email, invitation_token, data.full_name)
    
    return UserInviteResponse(
        detail=f"Invitación enviada a {data.email}",
        expires_at=expires_at
    )


@router.post("/accept-invitation", response_model=UserAcceptInvitationResponse, status_code=status.HTTP_201_CREATED)
def accept_invitation(
    data: UserAcceptInvitation,
    db: Session = Depends(get_db),
):
    """
    Permite a un usuario invitado aceptar la invitación y crear su cuenta.
    
    Flujo:
    1. Buscar token en tokens_confirmacion y validar
    2. Extraer email y client_id del token
    3. Crear usuario en Cognito con email_verified=True
    4. Crear registro en la tabla users
    5. Marcar token como usado
    6. Responder con información del usuario creado
    """
    
    # 1️⃣ Buscar token en la tabla tokens_confirmacion
    token_record = (
        db.query(TokenConfirmacion)
        .filter(
            TokenConfirmacion.token == data.token,
            TokenConfirmacion.type == TokenType.INVITATION,
        )
        .first()
    )
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de invitación inválido."
        )
    
    # 2️⃣ Validar que el token no haya sido usado
    if token_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este token ya ha sido utilizado."
        )
    
    # 3️⃣ Validar que el token no esté expirado
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de invitación expirado."
        )
    
    # 4️⃣ Extraer email, full_name y client_id del token
    email = token_record.email
    full_name = token_record.full_name
    client_id = token_record.client_id
    
    if not email or not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Datos de invitación incompletos."
        )
    
    # 5️⃣ Verificar que el usuario no exista (doble validación)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un usuario con el email {email}."
        )
    
    try:
        # 6️⃣ Crear usuario en Cognito con email verificado
        user_attributes = [
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
        ]
        
        # Agregar nombre si está disponible
        if full_name:
            user_attributes.append({"Name": "name", "Value": full_name})
        
        cognito_resp = cognito.admin_create_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email,
            UserAttributes=user_attributes,
            MessageAction="SUPPRESS",  # No enviar correo automático de Cognito
        )
        
        # 7️⃣ Establecer contraseña proporcionada por el usuario (permanente)
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email,
            Password=data.password,
            Permanent=True,  # Esto evita el estado FORCE_CHANGE_PASSWORD
        )
        
        # 8️⃣ Obtener el cognito_sub
        cognito_sub = next(
            (attr["Value"] for attr in cognito_resp["User"]["Attributes"] if attr["Name"] == "sub"),
            None
        )
        
        if not cognito_sub:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo obtener el identificador de Cognito."
            )
    
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "UsernameExistsException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya existe en Cognito."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear usuario en Cognito [{error_code}]: {e.response['Error'].get('Message', str(e))}"
        )
    
    # 9️⃣ Crear usuario en la base de datos
    new_user = User(
        email=email,
        full_name=full_name or email,  # Usar full_name del token o email como fallback
        client_id=client_id,
        cognito_sub=cognito_sub,
        is_master=False,
        email_verified=True,
    )
    
    db.add(new_user)
    
    # 🔟 Marcar token como usado
    token_record.used = True
    token_record.user_id = new_user.id  # Asociar el user_id creado
    
    db.commit()
    db.refresh(new_user)
    
    return UserAcceptInvitationResponse(
        detail="Usuario creado exitosamente.",
        user=new_user
    )
