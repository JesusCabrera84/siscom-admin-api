"""
Endpoints internos para gestión de clientes/organizaciones.

Estos endpoints están protegidos por tokens PASETO y están diseñados
para ser usados por aplicaciones administrativas internas como gac-web.

Requiere: Token PASETO con service="gac" y role="NEXUS_ADMIN"

NOTA: "Client" es un alias de "Organization" mantenido por compatibilidad.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import AuthResult, get_auth_cognito_or_paseto
from app.db.session import get_db
from app.models.organization import Organization, OrganizationStatus
from app.models.user import User
from app.schemas.client import ClientOut

router = APIRouter()

# Dependencia para autenticación PASETO (o Cognito para flexibilidad)
get_auth_for_internal_clients = get_auth_cognito_or_paseto(
    required_service="gac",
    required_role="NEXUS_ADMIN",
)


@router.get("", response_model=list[ClientOut])
def list_all_clients(
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
    status_filter: Optional[OrganizationStatus] = Query(
        None, alias="status", description="Filtrar por estado del cliente"
    ),
    search: Optional[str] = Query(
        None, description="Buscar por nombre (parcial, case-insensitive)"
    ),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
):
    """
    Lista todos los clientes/organizaciones del sistema.

    Solo accesible para administradores internos con token PASETO válido.

    Parámetros de filtrado:
    - status: Filtrar por estado (PENDING, ACTIVE, SUSPENDED, DELETED)
    - search: Buscar por nombre (búsqueda parcial)
    - limit: Máximo de resultados (default: 50, max: 200)
    - offset: Para paginación
    """
    query = db.query(Organization)

    # Aplicar filtros
    if status_filter:
        query = query.filter(Organization.status == status_filter)

    if search:
        query = query.filter(Organization.name.ilike(f"%{search}%"))

    # Ordenar por fecha de creación descendente
    query = query.order_by(Organization.created_at.desc())

    # Aplicar paginación
    organizations = query.offset(offset).limit(limit).all()

    return organizations


@router.get("/stats")
def get_clients_stats(
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
):
    """
    Obtiene estadísticas generales de los clientes/organizaciones.

    Retorna conteo por estado y total de clientes.
    """
    total = db.query(Organization).count()
    pending = db.query(Organization).filter(Organization.status == OrganizationStatus.PENDING).count()
    active = db.query(Organization).filter(Organization.status == OrganizationStatus.ACTIVE).count()
    suspended = db.query(Organization).filter(Organization.status == OrganizationStatus.SUSPENDED).count()
    deleted = db.query(Organization).filter(Organization.status == OrganizationStatus.DELETED).count()

    return {
        "total": total,
        "by_status": {
            "pending": pending,
            "active": active,
            "suspended": suspended,
            "deleted": deleted,
        },
    }


@router.get("/{client_id}", response_model=ClientOut)
def get_client_by_id(
    client_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
):
    """
    Obtiene un cliente/organización específico por su ID.

    Solo accesible para administradores internos con token PASETO válido.
    """
    organization = db.query(Organization).filter(Organization.id == client_id).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    return organization


@router.get("/{client_id}/users")
def get_client_users(
    client_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
):
    """
    Lista todos los usuarios de un cliente/organización específico.

    Útil para administración y soporte.
    """
    # Verificar que la organización existe
    organization = db.query(Organization).filter(Organization.id == client_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    users = db.query(User).filter(User.organization_id == client_id).all()

    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_master": user.is_master,
            "email_verified": user.email_verified,
            "has_cognito": user.cognito_sub is not None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]


@router.patch("/{client_id}/status")
def update_client_status(
    client_id: UUID,
    new_status: OrganizationStatus,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
):
    """
    Actualiza el estado de un cliente/organización.

    Permite suspender, activar o marcar como eliminado un cliente.

    Estados válidos:
    - PENDING: Cliente pendiente de verificación
    - ACTIVE: Cliente activo
    - SUSPENDED: Cliente suspendido
    - DELETED: Cliente eliminado lógicamente
    """
    organization = db.query(Organization).filter(Organization.id == client_id).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    old_status = organization.status
    organization.status = new_status
    db.commit()
    db.refresh(organization)

    return {
        "message": f"Estado actualizado de {old_status} a {new_status}",
        "client": {
            "id": str(organization.id),
            "name": organization.name,
            "status": organization.status,
        },
    }
