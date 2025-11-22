from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user_full,
    get_current_user_id,
)
from app.db.session import get_db
from app.models.device import Device, DeviceEvent
from app.models.unit import Unit
from app.models.unit_device import UnitDevice
from app.models.user import User
from app.models.user_unit import UserUnit
from app.schemas.device import DeviceOut
from app.schemas.unit import UnitCreate, UnitDetail, UnitOut, UnitUpdate, UnitWithDevice
from app.schemas.unit_device import UnitDeviceAssign, UnitDeviceOut
from app.schemas.user_unit import UserUnitAssign, UserUnitDetail

router = APIRouter()


# ============================================
# Helper Functions
# ============================================


def check_unit_access(
    db: Session, unit_id: UUID, user: User, required_role: str = None
) -> Unit:
    """
    Verifica que el usuario tenga acceso a la unidad.

    - Si es maestro: tiene acceso a todas las unidades del cliente
    - Si no es maestro: debe tener un registro en user_units
    - Si se especifica required_role: valida que tenga ese rol o superior

    Retorna la unidad si tiene acceso, lanza HTTPException si no.
    """
    # Obtener la unidad
    unit = (
        db.query(Unit)
        .filter(
            Unit.id == unit_id,
            Unit.client_id == user.client_id,
            Unit.deleted_at.is_(None),
        )
        .first()
    )

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada"
        )

    # Si es maestro, tiene acceso total
    if user.is_master:
        return unit

    # Si no es maestro, verificar en user_units
    user_unit = (
        db.query(UserUnit)
        .filter(UserUnit.user_id == user.id, UserUnit.unit_id == unit_id)
        .first()
    )

    if not user_unit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a esta unidad",
        )

    # Validar rol si se requiere
    if required_role:
        role_hierarchy = {"viewer": 0, "editor": 1, "admin": 2}
        user_role_level = role_hierarchy.get(user_unit.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_role_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol '{required_role}' o superior",
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
        user_unit_ids = (
            db.query(UserUnit.unit_id).filter(UserUnit.user_id == user.id).subquery()
        )

        return query.filter(Unit.id.in_(user_unit_ids)).all()


# ============================================
# Unit Endpoints
# ============================================


@router.get("", response_model=List[UnitWithDevice])
def list_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
    include_deleted: bool = False,
):
    """
    Lista las unidades visibles para el usuario autenticado con información del dispositivo asignado.

    - Si es maestro → todas las unidades del cliente
    - Si no es maestro → solo las unidades en user_units

    Incluye información del dispositivo actualmente asignado (si existe).

    Parámetros:
    - include_deleted: incluir unidades eliminadas (solo para maestros)
    """
    # Construir query base con LEFT JOINs
    query = (
        db.query(
            Unit.id,
            Unit.client_id,
            Unit.name,
            Unit.description,
            Unit.deleted_at,
            Device.device_id,
            Device.brand.label("device_brand"),
            Device.model.label("device_model"),
            UnitDevice.assigned_at,
        )
        .outerjoin(
            UnitDevice,
            (UnitDevice.unit_id == Unit.id) & (UnitDevice.unassigned_at.is_(None)),
        )
        .outerjoin(Device, Device.device_id == UnitDevice.device_id)
        .filter(Unit.client_id == current_user.client_id)
    )

    # Filtrar unidades eliminadas
    if not include_deleted:
        query = query.filter(Unit.deleted_at.is_(None))

    # Filtrar por permisos si no es maestro
    if not current_user.is_master:
        user_unit_ids = (
            db.query(UserUnit.unit_id)
            .filter(UserUnit.user_id == current_user.id)
            .subquery()
        )
        query = query.filter(Unit.id.in_(user_unit_ids))

    # Ejecutar query
    results = query.all()

    # Construir respuesta
    units = []
    for row in results:
        unit = UnitWithDevice(
            id=row.id,
            client_id=row.client_id,
            name=row.name,
            description=row.description,
            deleted_at=row.deleted_at,
            device_id=row.device_id,
            device_brand=row.device_brand,
            device_model=row.device_model,
            assigned_at=row.assigned_at,
        )
        units.append(unit)

    return units


@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
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
            detail="Solo los usuarios maestros pueden crear unidades",
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
    active_devices = (
        db.query(UnitDevice)
        .filter(UnitDevice.unit_id == unit_id, UnitDevice.unassigned_at.is_(None))
        .count()
    )

    total_devices = db.query(UnitDevice).filter(UnitDevice.unit_id == unit_id).count()

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
    unit = check_unit_access(db, unit_id, current_user, required_role="editor")

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
            detail="Solo los usuarios maestros pueden eliminar unidades",
        )

    # Verificar que la unidad existe y pertenece al cliente
    unit = (
        db.query(Unit)
        .filter(
            Unit.id == unit_id,
            Unit.client_id == current_user.client_id,
            Unit.deleted_at.is_(None),
        )
        .first()
    )

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada"
        )

    # Verificar si tiene dispositivos activos
    active_devices = (
        db.query(UnitDevice)
        .filter(UnitDevice.unit_id == unit_id, UnitDevice.unassigned_at.is_(None))
        .count()
    )

    if active_devices > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la unidad porque tiene {active_devices} dispositivo(s) activo(s) asignado(s)",
        )

    # Marcar como eliminada
    unit.deleted_at = datetime.utcnow()
    db.add(unit)
    db.commit()

    return {
        "message": "Unidad eliminada exitosamente",
        "unit_id": str(unit_id),
        "deleted_at": unit.deleted_at.isoformat(),
    }


# ============================================
# Hierarchical Endpoints (Nested Resources)
# ============================================


def create_device_event(
    db: Session,
    device_id: str,
    event_type: str,
    old_status: str = None,
    new_status: str = None,
    performed_by: UUID = None,
    event_details: str = None,
) -> DeviceEvent:
    """Crea un registro de evento para un dispositivo"""
    event = DeviceEvent(
        device_id=device_id,
        event_type=event_type,
        old_status=old_status,
        new_status=new_status,
        performed_by=performed_by,
        event_details=event_details,
    )
    db.add(event)
    return event


@router.get("/{unit_id}/device", response_model=Optional[DeviceOut])
def get_unit_device(
    unit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Devuelve el dispositivo actualmente asignado a una unidad.

    Requiere: Acceso a la unidad (maestro o en user_units).

    Retorna None si no hay dispositivo asignado actualmente.
    """
    # Verificar acceso a la unidad
    check_unit_access(db, unit_id, current_user)

    # Buscar asignación activa
    active_assignment = (
        db.query(UnitDevice)
        .filter(UnitDevice.unit_id == unit_id, UnitDevice.unassigned_at.is_(None))
        .first()
    )

    if not active_assignment:
        return None

    # Obtener información del dispositivo
    device = (
        db.query(Device).filter(Device.device_id == active_assignment.device_id).first()
    )

    return device


@router.post(
    "/{unit_id}/device",
    response_model=UnitDeviceOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_device_to_unit(
    unit_id: UUID,
    assignment: UnitDeviceAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Asigna o reemplaza el dispositivo de una unidad.

    Requiere: Usuario maestro O rol 'editor'/'admin' en user_units.

    Comportamiento:
    - Si la unidad ya tiene un dispositivo activo, lo desasigna automáticamente
    - Asigna el nuevo dispositivo
    - Actualiza el estado del dispositivo a 'asignado'
    - Crea eventos en device_events

    Body (JSON):
    {
        "device_id": "864537040123456"
    }
    """
    # Verificar acceso con rol editor o superior
    unit = check_unit_access(db, unit_id, current_user, required_role="editor")

    # Verificar que el dispositivo existe y pertenece al cliente
    device = (
        db.query(Device)
        .filter(
            Device.device_id == assignment.device_id,
            Device.client_id == current_user.client_id,
        )
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado o no pertenece a tu cliente",
        )

    # Validar estado del dispositivo
    if device.status not in ["entregado", "devuelto"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El dispositivo debe estar en estado 'entregado' o 'devuelto' (estado actual: {device.status})",
        )

    # Si la unidad ya tiene un dispositivo activo, desasignarlo primero
    current_assignment = (
        db.query(UnitDevice)
        .filter(UnitDevice.unit_id == unit_id, UnitDevice.unassigned_at.is_(None))
        .first()
    )

    if current_assignment:
        # Desasignar dispositivo anterior
        current_assignment.unassigned_at = datetime.utcnow()
        db.add(current_assignment)

        # Actualizar estado del dispositivo anterior
        old_device = (
            db.query(Device)
            .filter(Device.device_id == current_assignment.device_id)
            .first()
        )

        if old_device:
            old_device.status = "entregado"
            db.add(old_device)

            create_device_event(
                db=db,
                device_id=old_device.device_id,
                event_type="estado_cambiado",
                old_status="asignado",
                new_status="entregado",
                performed_by=user_id,
                event_details=f"Dispositivo desasignado de unidad '{unit.name}' (reemplazo)",
            )

    # Verificar que el nuevo dispositivo no esté asignado en otra unidad
    existing_assignment = (
        db.query(UnitDevice)
        .filter(
            UnitDevice.device_id == assignment.device_id,
            UnitDevice.unassigned_at.is_(None),
        )
        .first()
    )

    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El dispositivo ya está asignado a otra unidad activa",
        )

    # Crear nueva asignación
    new_assignment = UnitDevice(
        unit_id=unit_id,
        device_id=assignment.device_id,
        assigned_at=datetime.utcnow(),
    )
    db.add(new_assignment)

    # Actualizar estado del nuevo dispositivo
    old_status = device.status
    device.status = "asignado"
    device.last_assignment_at = datetime.utcnow()
    db.add(device)

    # Crear evento
    create_device_event(
        db=db,
        device_id=device.device_id,
        event_type="asignado",
        old_status=old_status,
        new_status="asignado",
        performed_by=user_id,
        event_details=f"Dispositivo asignado a unidad '{unit.name}'",
    )

    db.commit()
    db.refresh(new_assignment)

    return new_assignment


@router.get("/{unit_id}/users", response_model=List[UserUnitDetail])
def list_unit_users(
    unit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Lista los usuarios con acceso a una unidad específica.

    Requiere: Acceso a la unidad (maestro o en user_units).

    Retorna información detallada de cada usuario con acceso.
    """
    # Verificar acceso a la unidad
    unit = check_unit_access(db, unit_id, current_user)

    # Obtener asignaciones
    assignments = (
        db.query(UserUnit)
        .filter(UserUnit.unit_id == unit_id)
        .order_by(UserUnit.granted_at.desc())
        .all()
    )

    # Construir respuesta detallada
    result = []
    for assignment in assignments:
        user = db.query(User).filter(User.id == assignment.user_id).first()
        granted_by_user = None
        if assignment.granted_by:
            granted_by_user = (
                db.query(User).filter(User.id == assignment.granted_by).first()
            )

        detail = UserUnitDetail(
            id=assignment.id,
            user_id=assignment.user_id,
            unit_id=assignment.unit_id,
            granted_by=assignment.granted_by,
            granted_at=assignment.granted_at,
            role=assignment.role,
            user_email=user.email if user else None,
            user_full_name=user.full_name if user else None,
            unit_name=unit.name,
            granted_by_email=granted_by_user.email if granted_by_user else None,
        )
        result.append(detail)

    return result


@router.post("/{unit_id}/users", status_code=status.HTTP_201_CREATED)
def assign_user_to_unit(
    unit_id: UUID,
    assignment: UserUnitAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Asigna un usuario a una unidad con un rol específico.

    Requiere: Usuario maestro del cliente.

    Body (JSON):
    {
        "user_id": "abc12345-e89b-12d3-a456-426614174000",
        "role": "editor"  // opcional, default: "viewer"
    }

    Roles disponibles: viewer, editor, admin
    """
    # Validar que sea maestro
    if not current_user.is_master:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios maestros pueden asignar usuarios a unidades",
        )

    # Verificar que la unidad existe y pertenece al cliente
    unit = (
        db.query(Unit)
        .filter(
            Unit.id == unit_id,
            Unit.client_id == current_user.client_id,
            Unit.deleted_at.is_(None),
        )
        .first()
    )

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada"
        )

    # Verificar que el usuario existe y pertenece al cliente
    target_user = (
        db.query(User)
        .filter(User.id == assignment.user_id, User.client_id == current_user.client_id)
        .first()
    )

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado o no pertenece a tu cliente",
        )

    # No permitir asignar a usuarios maestros
    if target_user.is_master:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No es necesario asignar usuarios maestros (ya tienen acceso a todas las unidades)",
        )

    # Verificar que no existe una asignación previa
    existing = (
        db.query(UserUnit)
        .filter(UserUnit.user_id == assignment.user_id, UserUnit.unit_id == unit_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El usuario ya tiene acceso a esta unidad con rol '{existing.role}'",
        )

    # Crear la asignación
    user_unit = UserUnit(
        user_id=assignment.user_id,
        unit_id=unit_id,
        role=assignment.role,
        granted_by=current_user.id,
    )
    db.add(user_unit)
    db.commit()
    db.refresh(user_unit)

    return {
        "message": "Usuario asignado exitosamente",
        "assignment_id": str(user_unit.id),
        "user_email": target_user.email,
        "unit_name": unit.name,
        "role": assignment.role,
    }


@router.delete("/{unit_id}/users/{user_id}", status_code=status.HTTP_200_OK)
def remove_user_from_unit(
    unit_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Revoca el acceso de un usuario a una unidad.

    Requiere: Usuario maestro del cliente.

    Elimina la asignación usuario→unidad.
    """
    # Validar que sea maestro
    if not current_user.is_master:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios maestros pueden revocar accesos a unidades",
        )

    # Verificar que la unidad pertenece al cliente
    unit = (
        db.query(Unit)
        .filter(Unit.id == unit_id, Unit.client_id == current_user.client_id)
        .first()
    )

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada"
        )

    # Buscar la asignación
    assignment = (
        db.query(UserUnit)
        .filter(UserUnit.user_id == user_id, UserUnit.unit_id == unit_id)
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene acceso a esta unidad",
        )

    # Obtener información para el mensaje
    user = db.query(User).filter(User.id == user_id).first()

    # Eliminar la asignación
    db.delete(assignment)
    db.commit()

    return {
        "message": "Acceso revocado exitosamente",
        "user_email": user.email if user else None,
        "unit_name": unit.name,
    }
