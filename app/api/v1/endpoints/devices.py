from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_client_id,
    get_current_user_full,
    get_current_user_id,
)
from app.db.session import get_db
from app.models.client import Client
from app.models.device import Device, DeviceEvent
from app.models.unit import Unit
from app.models.unit_device import UnitDevice
from app.models.unit_profile import UnitProfile
from app.schemas.device import (
    DeviceCreate,
    DeviceOut,
    DeviceStatusUpdate,
    DeviceUpdate,
    DeviceWithProfileOut,
)

router = APIRouter()


# ============================================
# Helper Functions
# ============================================


def create_device_event(
    db: Session,
    device_id: str,
    event_type: str,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    performed_by: Optional[UUID] = None,
    event_details: Optional[str] = None,
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


# ============================================
# Device Endpoints
# ============================================


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    device_in: DeviceCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Registra un nuevo dispositivo en el inventario.

    Regla: El dispositivo se crea con status='nuevo' y sin cliente asignado.
    """
    # Verificar que el device_id no exista
    existing = db.query(Device).filter(Device.device_id == device_in.device_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El device_id ya está registrado",
        )

    # Crear dispositivo con status 'nuevo' y sin cliente
    device = Device(
        device_id=device_in.device_id,
        brand=device_in.brand,
        model=device_in.model,
        firmware_version=device_in.firmware_version,
        notes=device_in.notes,
        status="nuevo",
        client_id=None,  # Sin cliente asignado
    )
    db.add(device)

    # Registrar evento de creación
    create_device_event(
        db=db,
        device_id=device.device_id,
        event_type="creado",
        new_status="nuevo",
        performed_by=user_id,
        event_details=f"Dispositivo {device.brand} {device.model} registrado en inventario",
    )

    db.commit()
    db.refresh(device)

    return device


@router.get("", response_model=List[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None,
    client_id: Optional[UUID] = None,
    brand: Optional[str] = None,
):
    """
    Lista todos los dispositivos.

    Filtros disponibles:
    - status_filter: Filtrar por estado específico
    - client_id: Filtrar por cliente
    - brand: Filtrar por marca
    """
    query = db.query(Device)

    if status_filter:
        query = query.filter(Device.status == status_filter)

    if client_id:
        query = query.filter(Device.client_id == client_id)

    if brand:
        query = query.filter(Device.brand.ilike(f"%{brand}%"))

    devices = query.order_by(Device.created_at.desc()).all()
    return devices


@router.get("/my-devices", response_model=List[DeviceWithProfileOut])
def list_my_devices(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None,
):
    """
    Lista todos los dispositivos del cliente autenticado con información del perfil de la unidad asignada.

    Incluye:
    - Datos del dispositivo
    - Información de la unidad asignada (si tiene asignación activa)
    - Perfil de la unidad (color, icon_type, brand, model, year, serial, description)

    Se puede filtrar por estado.
    """
    # Query con JOINs para obtener información del perfil
    query = (
        db.query(
            Device.device_id,
            Device.brand,
            Device.model,
            Device.firmware_version,
            Device.client_id,
            Device.status,
            Device.last_comm_at,
            Device.created_at,
            Device.updated_at,
            Device.last_assignment_at,
            Device.notes,
            # Datos de la unidad asignada
            Unit.id.label("unit_id"),
            Unit.name.label("unit_name"),
            # Datos del perfil de la unidad
            UnitProfile.color.label("profile_color"),
            UnitProfile.icon_type.label("profile_icon_type"),
            UnitProfile.brand.label("profile_brand"),
            UnitProfile.model.label("profile_model"),
            UnitProfile.year.label("profile_year"),
            UnitProfile.serial.label("profile_serial"),
            UnitProfile.description.label("profile_description"),
        )
        .outerjoin(
            UnitDevice,
            (UnitDevice.device_id == Device.device_id)
            & (UnitDevice.unassigned_at.is_(None)),  # Solo asignaciones activas
        )
        .outerjoin(Unit, Unit.id == UnitDevice.unit_id)
        .outerjoin(UnitProfile, UnitProfile.unit_id == Unit.id)
        .filter(Device.client_id == client_id)
    )

    if status_filter:
        query = query.filter(Device.status == status_filter)

    results = query.order_by(Device.created_at.desc()).all()

    # Construir respuesta con los datos del perfil
    devices = []
    for row in results:
        device = DeviceWithProfileOut(
            device_id=row.device_id,
            brand=row.brand,
            model=row.model,
            firmware_version=row.firmware_version,
            client_id=row.client_id,
            status=row.status,
            last_comm_at=row.last_comm_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_assignment_at=row.last_assignment_at,
            notes=row.notes,
            unit_id=row.unit_id,
            unit_name=row.unit_name,
            profile_color=row.profile_color,
            profile_icon_type=row.profile_icon_type,
            profile_brand=row.profile_brand,
            profile_model=row.profile_model,
            profile_year=row.profile_year,
            profile_serial=row.profile_serial,
            profile_description=row.profile_description,
        )
        devices.append(device)

    return devices


@router.get("/unassigned", response_model=List[DeviceOut])
def list_unassigned_devices(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Lista dispositivos del cliente que no están asignados a ninguna unidad activamente.
    Estados válidos: 'preparado', 'enviado', 'entregado' o 'devuelto'

    Verifica que no exista una asignación activa en unit_devices.
    """
    # Subquery para obtener device_ids que tienen asignación activa
    # Una asignación es activa si unassigned_at es NULL
    active_assignments_subquery = (
        db.query(UnitDevice.device_id)
        .filter(UnitDevice.unassigned_at.is_(None))
        .subquery()
    )

    devices = (
        db.query(Device)
        .filter(
            Device.client_id == client_id,
            Device.status.in_(["preparado", "enviado", "entregado", "devuelto"]),
            ~Device.device_id.in_(active_assignments_subquery),
        )
        .all()
    )
    return devices


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: str,
    db: Session = Depends(get_db),
):
    """
    Obtiene el detalle de un dispositivo específico.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    return device


@router.patch("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: str,
    device_update: DeviceUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Actualiza información básica del dispositivo.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    update_data = device_update.model_dump(exclude_unset=True)

    # Si se actualiza firmware, registrar evento
    if (
        "firmware_version" in update_data
        and update_data["firmware_version"] != device.firmware_version
    ):
        old_version = device.firmware_version
        new_version = update_data["firmware_version"]
        create_device_event(
            db=db,
            device_id=device.device_id,
            event_type="firmware_actualizado",
            performed_by=user_id,
            event_details=f"Firmware actualizado de {old_version} a {new_version}",
        )

    for key, value in update_data.items():
        setattr(device, key, value)

    device.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device


@router.patch("/{device_id}/status", response_model=DeviceOut)
def update_device_status(
    device_id: str,
    status_update: DeviceStatusUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Actualiza el estado del dispositivo siguiendo las reglas de negocio.

    Reglas:
    - 'preparado': Requiere client_id, asigna el cliente al dispositivo
    - 'enviado': Debe estar en estado 'preparado', marca el dispositivo como enviado
    - 'entregado': Valida que tenga client_id asignado
    - 'asignado': Requiere unit_id, actualiza last_assignment_at
    - 'devuelto': Quita client_id, puede reintegrarse al inventario
    - 'inactivo': Baja definitiva, no puede reasignarse
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    old_status = device.status
    new_status = status_update.new_status

    # ============================================
    # Validaciones según el nuevo estado
    # ============================================

    if new_status == "preparado":
        # Requiere client_id
        if not status_update.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere client_id para preparar el dispositivo",
            )

        # Verificar que el cliente existe
        client = db.query(Client).filter(Client.id == status_update.client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        device.client_id = status_update.client_id
        device.status = "preparado"

        event_details = f"Dispositivo preparado para cliente {client.name}"

    elif new_status == "enviado":
        # Debe estar en estado 'preparado' antes de ser enviado
        if device.status != "preparado":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El dispositivo debe estar en estado 'preparado' antes de ser enviado",
            )

        device.status = "enviado"
        event_details = "Dispositivo enviado al cliente"

    elif new_status == "entregado":
        # Debe tener client_id
        if not device.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El dispositivo debe tener un cliente asignado",
            )

        device.status = "entregado"
        event_details = "Dispositivo entregado y confirmado por el cliente"

    elif new_status == "asignado":
        # Requiere unit_id
        if not status_update.unit_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere unit_id para asignar el dispositivo",
            )

        # Verificar que la unidad existe y pertenece al cliente del dispositivo
        unit = db.query(Unit).filter(Unit.id == status_update.unit_id).first()
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unidad no encontrada",
            )

        if device.client_id and unit.client_id != device.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La unidad no pertenece al cliente del dispositivo",
            )

        # Verificar si ya existe una asignación activa para este device
        # Una asignación es activa si unassigned_at es NULL
        existing_assignment = (
            db.query(UnitDevice)
            .filter(
                UnitDevice.device_id == device.device_id,
                UnitDevice.unassigned_at.is_(None),
            )
            .first()
        )

        if existing_assignment:
            # Desasignar de la unidad anterior
            existing_assignment.unassigned_at = datetime.utcnow()
            db.add(existing_assignment)

        # Crear nueva asignación en unit_devices
        unit_device = UnitDevice(
            unit_id=status_update.unit_id,
            device_id=device.device_id,
            assigned_at=datetime.utcnow(),
        )
        db.add(unit_device)

        device.status = "asignado"
        device.last_assignment_at = datetime.utcnow()

        event_details = f"Dispositivo asignado a unidad {unit.name}"

    elif new_status == "devuelto":
        # Desasignar de cualquier unidad activa
        # Una asignación es activa si unassigned_at es NULL
        active_assignment = (
            db.query(UnitDevice)
            .filter(
                UnitDevice.device_id == device.device_id,
                UnitDevice.unassigned_at.is_(None),
            )
            .first()
        )

        if active_assignment:
            active_assignment.unassigned_at = datetime.utcnow()
            db.add(active_assignment)

        # Quitar cliente
        device.client_id = None
        device.status = "devuelto"

        event_details = "Dispositivo devuelto al inventario"

    elif new_status == "inactivo":
        # Baja definitiva
        device.status = "inactivo"

        event_details = "Dispositivo dado de baja (inactivo)"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado '{new_status}' no válido",
        )

    # Agregar notas si se proporcionaron
    if status_update.notes:
        event_details += f" - {status_update.notes}"

    # Registrar evento
    create_device_event(
        db=db,
        device_id=device.device_id,
        event_type=new_status,  # El tipo de evento coincide con el nuevo estado
        old_status=old_status,
        new_status=new_status,
        performed_by=user_id,
        event_details=event_details,
    )

    device.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device


@router.post("/{device_id}/notes", response_model=DeviceOut)
def add_device_note(
    device_id: str,
    note: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Agrega una nota administrativa al dispositivo.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    # Registrar evento de nota
    create_device_event(
        db=db,
        device_id=device.device_id,
        event_type="nota",
        performed_by=user_id,
        event_details=note,
    )

    # Agregar a las notas del dispositivo
    if device.notes:
        device.notes += f"\n\n{datetime.utcnow().isoformat()}: {note}"
    else:
        device.notes = f"{datetime.utcnow().isoformat()}: {note}"

    device.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device


@router.get("/{device_id}/trips")
def get_device_trips(
    device_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_full),
    start_date: datetime = Query(
        ..., description="Fecha de inicio (ISO 8601, obligatorio)"
    ),
    end_date: datetime = Query(..., description="Fecha de fin (ISO 8601, obligatorio)"),
    limit: int = Query(50, ge=1, le=500, description="Límite de resultados"),
    cursor: Optional[datetime] = Query(
        None, description="Cursor de paginación (timestamp del último trip)"
    ),
    include_alerts: bool = Query(False, description="Incluir alertas en la respuesta"),
    include_points: bool = Query(
        False, description="Incluir puntos GPS en la respuesta"
    ),
    include_events: bool = Query(False, description="Incluir eventos en la respuesta"),
):
    """
    Obtiene los trips de un dispositivo específico en un rango de fechas.

    **IMPORTANTE:** Este endpoint requiere obligatoriamente `start_date` y `end_date`
    para optimizar las consultas en la base de datos Timescale.

    **Permisos:**
    - El usuario debe tener acceso a la unidad donde está o estuvo asignado el dispositivo.
    - Se valida que el dispositivo pertenezca al cliente del usuario autenticado.

    **Filtros obligatorios:**
    - `start_date`: Fecha de inicio del rango (ISO 8601)
    - `end_date`: Fecha de fin del rango (ISO 8601)

    **Filtros opcionales:**
    - `limit`: Número máximo de resultados (default: 50, max: 500)
    - `cursor`: Timestamp del último trip recibido (para paginación)

    **Expansiones:**
    - `include_alerts`: Incluye las alertas de cada trip
    - `include_points`: Incluye los puntos GPS de cada trip
    - `include_events`: Incluye los eventos de cada trip
    """
    from app.api.v1.endpoints.trips import (
        build_trip_detail,
        build_trip_out,
        check_device_access,
    )
    from app.models.trip import Trip
    from app.schemas.trip import TripListResponse

    # Verificar que el dispositivo existe y pertenece al cliente
    device = (
        db.query(Device)
        .filter(
            Device.device_id == device_id, Device.client_id == current_user.client_id
        )
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado o no pertenece a tu cliente",
        )

    # Verificar acceso al dispositivo
    if not check_device_access(db, device_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este dispositivo",
        )

    # Construir query con filtros obligatorios de fecha
    query = db.query(Trip).filter(
        Trip.device_id == device_id,
        Trip.start_time >= start_date,
        Trip.start_time <= end_date,
    )

    # Aplicar cursor de paginación
    if cursor:
        query = query.filter(Trip.start_time < cursor)

    # Contar total
    total = query.count()

    # Ordenar y limitar
    trips = query.order_by(Trip.start_time.desc()).limit(limit + 1).all()

    # Determinar si hay más resultados
    has_more = len(trips) > limit
    if has_more:
        trips = trips[:limit]

    # Construir respuesta
    if include_alerts or include_points or include_events:
        trip_list = [
            build_trip_detail(
                db,
                trip,
                include_alerts=include_alerts,
                include_points=include_points,
                include_events=include_events,
            )
            for trip in trips
        ]
    else:
        trip_list = [build_trip_out(trip) for trip in trips]

    # Calcular nuevo cursor
    new_cursor = None
    if trips:
        new_cursor = trips[-1].start_time.isoformat()

    return TripListResponse(
        trips=trip_list,
        total=total,
        limit=limit,
        cursor=new_cursor if has_more else None,
        has_more=has_more,
    )
