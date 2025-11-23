from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_client_id
from app.db.session import get_db
from app.models.client import Client, ClientStatus
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.models.user import User
from app.schemas.client import ClientCreate, ClientOut
from app.services.notifications import send_verification_email
from app.utils.security import generate_verification_token

router = APIRouter()


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
