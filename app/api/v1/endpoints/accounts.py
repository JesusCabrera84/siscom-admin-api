"""
Endpoints de Gestión de Accounts.

MODELO CONCEPTUAL:
==================
Account = Raíz comercial (billing, facturación)
- Puede tener múltiples Organizations
- Controla la información comercial y de facturación

ENDPOINTS:
==========
- GET /accounts/{account_id}: Obtiene información del account
- PATCH /accounts/{account_id}: Actualiza perfil progresivo del account

REGLA DE ORO:
=============
Los nombres NO son identidad. Los UUID sí.
❌ NO validar unicidad por account_name
✅ Solo usuarios master/owner pueden modificar
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthResult,
    get_current_organization_id,
    get_current_user_full,
    require_organization_role,
)
from app.db.session import get_db
from app.models.account import Account
from app.models.organization import Organization
from app.models.user import User
from app.schemas.account import AccountOut, AccountUpdate, AccountUpdateResponse
from app.services.organization import OrganizationService

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_account_for_user(db: Session, user: User) -> Account:
    """
    Obtiene el Account asociado al usuario a través de su organización.

    Args:
        db: Sesión de base de datos
        user: Usuario autenticado

    Returns:
        Account asociado al usuario

    Raises:
        HTTPException: Si no se encuentra la organización o el account
    """
    organization = (
        db.query(Organization).filter(Organization.id == user.organization_id).first()
    )
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organización no encontrada",
        )

    account = db.query(Account).filter(Account.id == organization.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account no encontrado",
        )

    return account


@router.get("/me", response_model=AccountOut)
def get_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Obtiene el Account del usuario autenticado.

    Resuelve el Account a través de la organización del usuario.
    """
    account = _get_account_for_user(db, current_user)
    return account


@router.get("/{account_id}", response_model=AccountOut)
def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Obtiene información de un Account específico.

    Verifica que el usuario tenga acceso al account solicitado.
    """
    # Verificar que el account existe
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account no encontrado",
        )

    # Verificar que el usuario tiene acceso (su organización pertenece al account)
    user_org = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )

    if not user_org or user_org.account_id != account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este account",
        )

    return account


@router.patch("/{account_id}", response_model=AccountUpdateResponse)
def update_account(
    account_id: UUID,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(require_organization_role("owner")),
):
    """
    Actualiza el perfil de un Account (perfil progresivo).

    Este endpoint permite completar o actualizar la información del Account
    de forma progresiva. Todos los campos son opcionales.

    PERMISOS:
    =========
    Solo usuarios con rol 'owner' pueden modificar el Account.

    CAMPOS ACTUALIZABLES:
    =====================
    - account_name: Nombre de la cuenta/empresa (puede repetirse, NO unicidad)
    - billing_email: Email de facturación
    - country: Código de país ISO
    - timezone: Zona horaria IANA
    - metadata: Metadatos adicionales

    VALIDACIONES:
    =============
    ❌ NO se exigen campos fiscales
    ❌ NO se valida unicidad por nombre
    ✅ billing_email puede ser único si existe

    Returns:
        AccountUpdateResponse con información actualizada
    """
    # Verificar que el account existe
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account no encontrado",
        )

    # Verificar que el usuario pertenece a una organización de este account
    user_org = (
        db.query(Organization)
        .filter(Organization.id == auth.organization_id)
        .first()
    )

    if not user_org or user_org.account_id != account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este account",
        )

    # Actualizar solo los campos proporcionados
    update_data = data.model_dump(exclude_unset=True)

    if "account_name" in update_data:
        account.name = update_data["account_name"]
        # También actualizar nombre de la organización default si coincide
        if user_org.name == account.name or not user_org.name:
            user_org.name = update_data["account_name"]

    if "billing_email" in update_data:
        account.billing_email = update_data["billing_email"]
        # Propagar a la organización
        user_org.billing_email = update_data["billing_email"]

    if "country" in update_data:
        account.country = update_data["country"]
        user_org.country = update_data["country"]

    if "timezone" in update_data:
        account.timezone = update_data["timezone"]
        user_org.timezone = update_data["timezone"]

    if "metadata" in update_data:
        # Merge de metadata existente con nueva
        if account.account_metadata is None:
            account.account_metadata = {}
        if update_data["metadata"] is not None:
            account.account_metadata = {
                **account.account_metadata,
                **update_data["metadata"],
            }

    # Actualizar timestamp
    account.updated_at = datetime.utcnow()
    user_org.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(account)

    logger.info(f"[ACCOUNT UPDATE] Account {account_id} actualizado por user {auth.user_id}")

    return AccountUpdateResponse(
        id=account.id,
        account_name=account.name,
        billing_email=account.billing_email,
        country=account.country,
        timezone=account.timezone or "UTC",
        updated_at=account.updated_at,
    )

