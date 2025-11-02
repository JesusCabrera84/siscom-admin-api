from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.api.deps import get_current_client_id
from app.models.client import Client, ClientStatus
from app.models.user import User
from app.schemas.client import ClientOut, ClientCreate
from app.utils.security import hash_password, generate_verification_token
from app.core.config import settings
from botocore.exceptions import ClientError
import boto3

router = APIRouter()

# ------------------------------------------
# Cognito client
# ------------------------------------------
cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
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
            status_code=400,
            detail="Ya existe un usuario con este correo electrónico."
        )
    
    # 🔍 Verificar que el nombre del cliente no exista
    existing_name = db.query(Client).filter(Client.name == data.name).first()
    if existing_name:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un cliente con este nombre."
        )
    
    # 1️⃣ Crear registro temporal del cliente (status PENDING)
    client = Client(
        name=data.name,
        status=ClientStatus.PENDING,  # Estado temporal hasta verificar email
    )
    db.add(client)
    db.flush()  # Para obtener el id del cliente
    
    # 2️⃣ Hashear la contraseña
    password_hashed = hash_password(data.password)
    
    # 3️⃣ Generar token de verificación
    verification_token = generate_verification_token()
    
    # 4️⃣ Crear usuario master asociado al cliente
    user = User(
        client_id=client.id,
        email=data.email,
        full_name=data.name,
        is_master=True,
        password_hash=password_hashed,
        verification_token=verification_token,
        email_verified=False,
        # cognito_sub se asignará después de la verificación
    )
    db.add(user)
    db.commit()
    db.refresh(client)
    db.refresh(user)
    
    # TODO: 5️⃣ Enviar correo de verificación
    # Aquí se enviará un correo con el verification_token
    # URL ejemplo: https://tu-app.com/verify-email?token={verification_token}
    # await send_verification_email(user.email, verification_token)
    
    return client


@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verifica el email del usuario mediante el token enviado por correo.
    
    Flujo:
    1. Buscar usuario con el token de verificación
    2. Crear usuario en Cognito con email_verified=true
    3. Actualizar usuario con cognito_sub y email_verified=true
    4. Actualizar cliente a status ACTIVE
    5. Limpiar verification_token
    """
    
    # 1️⃣ Buscar usuario con el token
    user = db.query(User).filter(User.verification_token == token).first()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Token de verificación inválido o expirado."
        )
    
    if user.email_verified:
        raise HTTPException(
            status_code=400,
            detail="Este email ya ha sido verificado."
        )
    
    # 2️⃣ Buscar el cliente asociado
    client = db.query(Client).filter(Client.id == user.client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado."
        )
    
    try:
        # 3️⃣ Crear usuario en Cognito con email verificado
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
        
        # 4️⃣ Establecer contraseña temporal en Cognito
        # El usuario recibirá un correo de Cognito para establecer su contraseña
        # O pueden usar el flujo de "forgot password" después de verificar el email
        # Otra opción: usar admin_create_user sin MessageAction="SUPPRESS" 
        # para que Cognito envíe el correo con contraseña temporal
        
        # Obtener el cognito_sub
        cognito_sub = cognito_resp["User"]["Attributes"][0]["Value"]
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "UsernameExistsException":
            raise HTTPException(
                status_code=400,
                detail="El usuario ya existe en Cognito."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear usuario en Cognito: {str(e)}"
        )
    
    # 5️⃣ Actualizar usuario en la base de datos
    user.cognito_sub = cognito_sub
    user.email_verified = True
    user.verification_token = None  # Limpiar el token
    
    # 6️⃣ Actualizar cliente a ACTIVE
    client.status = ClientStatus.ACTIVE
    
    db.commit()
    
    return {
        "message": "Email verificado exitosamente. Tu cuenta ha sido activada.",
        "email": user.email,
        "client_id": str(client.id)
    }


@router.get("/", response_model=ClientOut)
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
