"""
Endpoints de Onboarding y Gestión de Clientes.

MODELO CONCEPTUAL:
==================
Account = Raíz comercial (billing, facturación)
Organization = Raíz operativa (permisos, uso diario)

ONBOARDING RÁPIDO (POST /clients):
==================================
1. Crear Account
2. Crear Organization default
3. Crear User master
4. Registrar usuario en Cognito
5. Enviar email de verificación

REGLA DE ORO:
=============
Los nombres NO son identidad. Los UUID sí.
❌ NO validar unicidad por account_name
❌ NO validar unicidad global por organization.name
✅ User.email debe ser único (global)
✅ Organization.name único solo dentro del mismo account
"""

import logging
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.core.config import settings
from app.db.session import get_db
from app.models.account import Account, AccountStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.organization_user import OrganizationRole, OrganizationUser
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.models.user import User
from app.schemas.client import ClientOut, OnboardingRequest, OnboardingResponse
from app.services.notifications import send_verification_email
from app.utils.security import generate_verification_token

logger = logging.getLogger(__name__)

router = APIRouter()

# Cliente de Cognito
cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)


@router.post("", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
def create_client(data: OnboardingRequest, db: Session = Depends(get_db)):
    """
    Onboarding rápido - Crea Account + Organization + User.

    Este endpoint representa el alta inicial de una cuenta, NO el perfil completo.
    Soporta onboarding progresivo para personas, familias y empresas.

    FLUJO OBLIGATORIO:
    ==================
    1. Validar que el email NO exista en users (única validación de unicidad)
    2. Crear Account (account_name = input.account_name)
    3. Crear Organization default (name = input.account_name)
    4. Crear User master
    5. Crear membership OWNER en organization_users
    6. Registrar usuario en Cognito
    7. Enviar email de verificación (no falla el endpoint si falla el envío)

    VALIDACIONES PROHIBIDAS:
    ========================
    ❌ NO validar unicidad por account_name
    ❌ NO validar unicidad global por organization.name
    ❌ NO usar client_id
    ❌ NO usar active_subscription_id

    VALIDACIONES PERMITIDAS:
    ========================
    ✅ User.email debe ser único (global)

    Returns:
        OnboardingResponse con account_id, organization_id, user_id
    """

    # =========================================
    # 1️⃣ ÚNICA VALIDACIÓN: Email debe ser único
    # =========================================
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este correo electrónico.",
        )

    # =========================================
    # 2️⃣ Crear Account (raíz comercial)
    # =========================================
    account = Account(
        name=data.account_name,
        billing_email=data.billing_email or data.email,  # Fallback a email del usuario
        country=data.country,
        timezone=data.timezone or "UTC",
        status=AccountStatus.ACTIVE,
    )
    db.add(account)
    db.flush()  # Para obtener el id del account

    # =========================================
    # 3️⃣ Crear Organization default
    # =========================================
    organization = Organization(
        account_id=account.id,
        name=data.account_name,  # Mismo nombre que account
        billing_email=data.billing_email or data.email,
        country=data.country,
        timezone=data.timezone or "UTC",
        status=OrganizationStatus.ACTIVE,  # Activo desde el inicio
    )
    db.add(organization)
    db.flush()

    # =========================================
    # 4️⃣ Crear User master
    # =========================================
    user = User(
        organization_id=organization.id,
        email=data.email,
        full_name=data.account_name,  # Usar account_name como nombre inicial
        is_master=True,  # LEGACY: Se mantiene por compatibilidad
        email_verified=False,  # Pendiente de verificación
    )
    db.add(user)
    db.flush()

    # =========================================
    # 5️⃣ Crear membership OWNER
    # =========================================
    membership = OrganizationUser(
        organization_id=organization.id,
        user_id=user.id,
        role=OrganizationRole.OWNER,
    )
    db.add(membership)
    db.flush()

    # =========================================
    # 6️⃣ Registrar usuario en Cognito
    # =========================================
    cognito_sub = None
    try:
        # Crear usuario en Cognito
        cognito_response = cognito.admin_create_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=data.email,
            UserAttributes=[
                {"Name": "email", "Value": data.email},
                {"Name": "email_verified", "Value": "false"},
                {"Name": "name", "Value": data.account_name},
            ],
            MessageAction="SUPPRESS",  # No enviar email de Cognito, usamos el nuestro
        )

        # Obtener cognito_sub
        cognito_sub = next(
            (
                attr["Value"]
                for attr in cognito_response["User"]["Attributes"]
                if attr["Name"] == "sub"
            ),
            None,
        )

        # Establecer contraseña permanente
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=data.email,
            Password=data.password,
            Permanent=True,
        )

        # Actualizar usuario con cognito_sub
        if cognito_sub:
            user.cognito_sub = cognito_sub

        logger.info(f"[ONBOARDING] Usuario registrado en Cognito: {data.email}")

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))

        logger.error(
            f"[ONBOARDING ERROR] Cognito: {error_code} - {error_message} - Email: {data.email}"
        )

        # Si el usuario ya existe en Cognito, intentar obtener el sub
        if error_code == "UsernameExistsException":
            try:
                existing_cognito_user = cognito.admin_get_user(
                    UserPoolId=settings.COGNITO_USER_POOL_ID,
                    Username=data.email,
                )
                cognito_sub = next(
                    (
                        attr["Value"]
                        for attr in existing_cognito_user["UserAttributes"]
                        if attr["Name"] == "sub"
                    ),
                    None,
                )
                if cognito_sub:
                    user.cognito_sub = cognito_sub
                    logger.info(
                        f"[ONBOARDING] Usuario ya existía en Cognito, reutilizando: {data.email}"
                    )
            except Exception as inner_e:
                logger.error(
                    f"[ONBOARDING ERROR] No se pudo obtener usuario existente de Cognito: {inner_e}"
                )
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al configurar la cuenta. Por favor, contacte soporte.",
                )
        else:
            # Otro error de Cognito, hacer rollback
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al registrar usuario: {error_message}",
            )

    # =========================================
    # 7️⃣ Generar token y enviar email de verificación
    # =========================================
    verification_token_str = generate_verification_token()
    token = TokenConfirmacion(
        token=verification_token_str,
        user_id=user.id,
        type=TokenType.EMAIL_VERIFICATION,
        password_temp=data.password,  # Guardar temporalmente para flujo de verificación
    )
    db.add(token)

    # Commit de toda la transacción
    db.commit()
    db.refresh(account)
    db.refresh(organization)
    db.refresh(user)

    # Enviar email de verificación (NO falla el endpoint si falla)
    try:
        email_sent = send_verification_email(data.email, verification_token_str)
        if email_sent:
            logger.info(f"[ONBOARDING] Email de verificación enviado a: {data.email}")
        else:
            logger.warning(
                f"[ONBOARDING] No se pudo enviar email de verificación a: {data.email}"
            )
    except Exception as e:
        logger.warning(f"[ONBOARDING] Error enviando email de verificación: {e}")
        # NO hacer rollback, el usuario ya está creado

    # =========================================
    # 8️⃣ Retornar response
    # =========================================
    return OnboardingResponse(
        account_id=account.id,
        organization_id=organization.id,
        user_id=user.id,
    )


@router.get("", response_model=ClientOut)
def get_client_info(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene la información de la organización del usuario autenticado.

    Requiere autenticación con token de Cognito.
    """
    organization = (
        db.query(Organization).filter(Organization.id == organization_id).first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organización no encontrada",
        )

    return organization
