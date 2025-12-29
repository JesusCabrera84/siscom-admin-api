"""
Endpoints de Clientes/Organizaciones.

NOTA: "Client" es un alias de "Organization" mantenido por compatibilidad.
En el modelo conceptual actual:
- Account = Raíz comercial (billing)
- Organization = Raíz operativa (permisos, uso diario)

Onboarding:
1. Se crea Account
2. Se crea Organization (default, pertenece a Account)
3. Se crea User (owner de Organization)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.account import Account, AccountStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.organization_user import OrganizationRole, OrganizationUser
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.models.user import User
from app.schemas.client import ClientCreate, ClientOut
from app.services.notifications import send_verification_email
from app.utils.security import generate_verification_token

router = APIRouter()


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo cliente (Account + Organization + User owner).
    
    El proceso completo es:
    1. Validar que no exista el email en users
    2. Validar que no exista el nombre del cliente
    3. Crear Account (raíz comercial)
    4. Crear Organization (raíz operativa, pertenece a Account)
    5. Crear User (owner de la Organization)
    6. Crear membership con rol OWNER
    7. Enviar correo de verificación
    """

    # 🔍 Verificar que el email no exista en usuarios
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Ya existe un usuario con este correo electrónico."
        )

    # 🔍 Verificar que el nombre del cliente no exista
    existing_name = db.query(Organization).filter(Organization.name == data.name).first()
    if existing_name:
        raise HTTPException(
            status_code=400, detail="Ya existe un cliente con este nombre."
        )

    # 1️⃣ Crear Account (raíz comercial) - SIEMPRE existe
    account = Account(
        name=data.name,
        status=AccountStatus.ACTIVE,
    )
    db.add(account)
    db.flush()  # Para obtener el id del account

    # 2️⃣ Crear Organization (raíz operativa, pertenece a Account)
    organization = Organization(
        account_id=account.id,
        name=data.name,
        status=OrganizationStatus.PENDING,  # Estado temporal hasta verificar email
    )
    db.add(organization)
    db.flush()  # Para obtener el id de la organización

    # 3️⃣ Crear usuario owner asociado a la organización
    user = User(
        organization_id=organization.id,
        email=data.email,
        full_name=data.name,
        is_master=True,  # LEGACY: Se mantiene por compatibilidad
        email_verified=False,
        # password_hash no se usa, la autenticación es con Cognito
        # cognito_sub se asignará después de la verificación
    )
    db.add(user)
    db.flush()  # Para obtener el id del usuario

    # 4️⃣ Crear membership en organization_users con rol OWNER
    # Esta es la FUENTE DE VERDAD para roles organizacionales
    # is_master se mantiene solo como fallback legacy
    membership = OrganizationUser(
        organization_id=organization.id,
        user_id=user.id,
        role=OrganizationRole.OWNER,
    )
    db.add(membership)
    db.flush()

    # 5️⃣ Generar token de verificación y guardar la contraseña temporalmente
    verification_token_str = generate_verification_token()
    token = TokenConfirmacion(
        token=verification_token_str,
        user_id=user.id,
        type=TokenType.EMAIL_VERIFICATION,
        password_temp=data.password,  # Guardar contraseña temporalmente para Cognito
    )
    db.add(token)
    db.commit()
    db.refresh(organization)
    db.refresh(user)

    # 6️⃣ Enviar correo de verificación
    email_sent = send_verification_email(user.email, verification_token_str)
    if not email_sent:
        print(f"[WARNING] No se pudo enviar el correo de verificación a {user.email}")

    return organization


@router.get("", response_model=ClientOut)
def get_client_info(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene la información de la organización del usuario autenticado.
    """
    organization = db.query(Organization).filter(Organization.id == organization_id).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organización no encontrada",
        )

    return organization
