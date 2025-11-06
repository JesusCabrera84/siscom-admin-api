from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from datetime import datetime
from app.db.session import get_db
from app.api.deps import get_current_client_id, get_current_user_full, get_current_user_id
from app.models.unit import Unit
from app.models.user_unit import UserUnit
from app.models.unit_device import UnitDevice
from app.models.user import User
from app.schemas.unit import UnitCreate, UnitUpdate, UnitOut, UnitDetail

router = APIRouter()


# ============================================
# Helper Functions
# ============================================

def check_unit_access(
    db: Session,
    unit_id: UUID,
    user: User,
    required_role: str = None
) -> Unit:
    """
    Verifica que el usuario tenga acceso a la unidad.
    
    - Si es maestro: tiene acceso a todas las unidades del cliente
    - Si no es maestro: debe tener un registro en user_units
    - Si se especifica required_role: valida que tenga ese rol o superior
    
    Retorna la unidad si tiene acceso, lanza HTTPException si no.
    """
    # Obtener la unidad
    unit = db.query(Unit).filter(
        Unit.id == unit_id,
        Unit.client_id == user.client_id,
        Unit.deleted_at.is_(None)
    ).first()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidad no encontrada"
        )
    
    # Si es maestro, tiene acceso total
    if user.is_master:
        return unit
    
    # Si no es maestro, verificar en user_units
    user_unit = db.query(UserUnit).filter(
        UserUnit.user_id == user.id,
        UserUnit.unit_id == unit_id
    ).first()
    
    if not user_unit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a esta unidad"
        )
    
    # Validar rol si se requiere
    if required_role:
        role_hierarchy = {'viewer': 0, 'editor': 1, 'admin': 2}
        user_role_level = role_hierarchy.get(user_unit.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_role_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol '{required_role}' o superior"
            )
    
    return unit


def get_units_for_user(db: Session, user: User, include_deleted: bool = False):
    """
    Retorna las unidades visibles para el usuario.
    
    - Si es maestro: todas las del cliente
    - Si no es maestro: solo las que tiene en user_units
    """
    query = db.query(Unit).filter(Unit.client_id == user.client_id)
    
    if not include_deleted:
        query = query.filter(Unit.deleted_at.is_(None))
    
    if user.is_master:
        # Maestro ve todas las unidades del cliente
        return query.all()
    else:
        # Usuario normal ve solo las unidades con permisos
        user_unit_ids = db.query(UserUnit.unit_id).filter(
            UserUnit.user_id == user.id
        ).subquery()
        
        return query.filter(Unit.id.in_(user_unit_ids)).all()


# ============================================
# Unit Endpoints
# ============================================

@router.get("/", response_model=List[UnitOut])
def list_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
    include_deleted: bool = False,
):
    """
    Lista las unidades visibles para el usuario autenticado.
    
    - Si es maestro → todas las unidades del cliente
    - Si no es maestro → solo las unidades en user_units
    
    Parámetros:
    - include_deleted: incluir unidades eliminadas (solo para maestros)
    """
    units = get_units_for_user(db, current_user, include_deleted)
    return units


@router.post("/", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(
    unit: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Crea una nueva unidad.
    
    Requiere: Usuario maestro del cliente.
    """
    # Validar que sea maestro
    if not current_user.is_master:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios maestros pueden crear unidades"
        )
    
    # Crear la unidad
    new_unit = Unit(
        client_id=current_user.client_id,
        name=unit.name,
        description=unit.description,
    )
    db.add(new_unit)
    db.commit()
    db.refresh(new_unit)
    
    return new_unit


@router.get("/{unit_id}", response_model=UnitDetail)
def get_unit(
    unit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Obtiene el detalle de una unidad.
    
    Incluye contadores de dispositivos asignados.
    Requiere: Acceso a la unidad (maestro o en user_units).
    """
    # Verificar acceso
    unit = check_unit_access(db, unit_id, current_user)
    
    # Contar dispositivos
    active_devices = db.query(UnitDevice).filter(
        UnitDevice.unit_id == unit_id,
        UnitDevice.unassigned_at.is_(None)
    ).count()
    
    total_devices = db.query(UnitDevice).filter(
        UnitDevice.unit_id == unit_id
    ).count()
    
    # Construir respuesta
    detail = UnitDetail(
        id=unit.id,
        client_id=unit.client_id,
        name=unit.name,
        description=unit.description,
        deleted_at=unit.deleted_at,
        active_devices_count=active_devices,
        total_devices_count=total_devices,
    )
    
    return detail


@router.patch("/{unit_id}", response_model=UnitOut)
def update_unit(
    unit_id: UUID,
    unit_update: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Actualiza los datos de una unidad.
    
    Requiere: 
    - Usuario maestro, o
    - Usuario con rol 'editor' o 'admin' en user_units
    """
    # Verificar acceso con rol editor o superior
    unit = check_unit_access(db, unit_id, current_user, required_role='editor')
    
    # Actualizar campos
    update_data = unit_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(unit, field, value)
    
    db.add(unit)
    db.commit()
    db.refresh(unit)
    
    return unit


@router.delete("/{unit_id}", status_code=status.HTTP_200_OK)
def delete_unit(
    unit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Marca una unidad como eliminada (soft delete).
    
    No elimina físicamente el registro, solo marca deleted_at = NOW().
    
    Requiere: Usuario maestro del cliente.
    """
    # Solo maestros pueden eliminar
    if not current_user.is_master:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios maestros pueden eliminar unidades"
        )
    
    # Verificar que la unidad existe y pertenece al cliente
    unit = db.query(Unit).filter(
        Unit.id == unit_id,
        Unit.client_id == current_user.client_id,
        Unit.deleted_at.is_(None)
    ).first()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidad no encontrada"
        )
    
    # Verificar si tiene dispositivos activos
    active_devices = db.query(UnitDevice).filter(
        UnitDevice.unit_id == unit_id,
        UnitDevice.unassigned_at.is_(None)
    ).count()
    
    if active_devices > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la unidad porque tiene {active_devices} dispositivo(s) activo(s) asignado(s)"
        )
    
    # Marcar como eliminada
    unit.deleted_at = datetime.utcnow()
    db.add(unit)
    db.commit()
    
    return {
        "message": "Unidad eliminada exitosamente",
        "unit_id": str(unit_id),
        "deleted_at": unit.deleted_at.isoformat()
    }

