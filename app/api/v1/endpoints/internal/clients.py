"""
Endpoints internos para gestión de clientes.

Estos endpoints están protegidos por tokens PASETO y están diseñados
para ser usados por aplicaciones administrativas internas como gac-web.

Requiere: Token PASETO con service="gac" y role="NEXUS_ADMIN"
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import AuthResult, get_auth_cognito_or_paseto
from app.db.session import get_db
from app.models.client import Client, ClientStatus
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
    status_filter: Optional[ClientStatus] = Query(
        None, alias="status", description="Filtrar por estado del cliente"
    ),
    search: Optional[str] = Query(
        None, description="Buscar por nombre (parcial, case-insensitive)"
    ),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
):
    """
    Lista todos los clientes del sistema.

    Solo accesible para administradores internos con token PASETO válido.

    Parámetros de filtrado:
    - status: Filtrar por estado (PENDING, ACTIVE, SUSPENDED, DELETED)
    - search: Buscar por nombre (búsqueda parcial)
    - limit: Máximo de resultados (default: 50, max: 200)
    - offset: Para paginación
    """
    query = db.query(Client)

    # Aplicar filtros
    if status_filter:
        query = query.filter(Client.status == status_filter)

    if search:
        query = query.filter(Client.name.ilike(f"%{search}%"))

    # Ordenar por fecha de creación descendente
    query = query.order_by(Client.created_at.desc())

    # Aplicar paginación
    clients = query.offset(offset).limit(limit).all()

    return clients


@router.get("/stats")
def get_clients_stats(
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
):
    """
    Obtiene estadísticas generales de los clientes.

    Retorna conteo por estado y total de clientes.
    """
    total = db.query(Client).count()
    pending = db.query(Client).filter(Client.status == ClientStatus.PENDING).count()
    active = db.query(Client).filter(Client.status == ClientStatus.ACTIVE).count()
    suspended = db.query(Client).filter(Client.status == ClientStatus.SUSPENDED).count()
    deleted = db.query(Client).filter(Client.status == ClientStatus.DELETED).count()

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
    Obtiene un cliente específico por su ID.

    Solo accesible para administradores internos con token PASETO válido.
    """
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    return client


@router.get("/{client_id}/users")
def get_client_users(
    client_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
):
    """
    Lista todos los usuarios de un cliente específico.

    Útil para administración y soporte.
    """
    # Verificar que el cliente existe
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    users = db.query(User).filter(User.client_id == client_id).all()

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
    new_status: ClientStatus,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_auth_for_internal_clients),
):
    """
    Actualiza el estado de un cliente.

    Permite suspender, activar o marcar como eliminado un cliente.

    Estados válidos:
    - PENDING: Cliente pendiente de verificación
    - ACTIVE: Cliente activo
    - SUSPENDED: Cliente suspendido
    - DELETED: Cliente eliminado lógicamente
    """
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    old_status = client.status
    client.status = new_status
    db.commit()
    db.refresh(client)

    return {
        "message": f"Estado actualizado de {old_status} a {new_status}",
        "client": {
            "id": str(client.id),
            "name": client.name,
            "status": client.status,
        },
    }
