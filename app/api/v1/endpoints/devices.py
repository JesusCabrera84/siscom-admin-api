from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.db.session import get_db
from app.api.deps import get_current_client_id
from app.models.device import Device
from app.schemas.device import DeviceOut, DeviceCreate

router = APIRouter()


@router.get("/", response_model=List[DeviceOut])
def list_devices(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
    active: Optional[bool] = None,
):
    """
    Lista todos los dispositivos del cliente autenticado.
    Se puede filtrar por estado activo/inactivo.
    """
    query = db.query(Device).filter(Device.client_id == client_id)

    if active is not None:
        query = query.filter(Device.active == active)

    devices = query.all()
    return devices


@router.get("/unassigned", response_model=List[DeviceOut])
def list_unassigned_devices(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Lista dispositivos que no están instalados en ninguna unidad.
    """
    devices = (
        db.query(Device)
        .filter(
            Device.client_id == client_id,
            Device.installed_in_unit_id.is_(None),
        )
        .all()
    )
    return devices


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: UUID,
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene el detalle de un dispositivo específico.
    """
    device = (
        db.query(Device)
        .filter(
            Device.id == device_id,
            Device.client_id == client_id,
        )
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    return device


@router.post("/", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    device_in: DeviceCreate,
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Registra un nuevo dispositivo al cliente.
    """
    # Verificar que el IMEI no exista
    existing = db.query(Device).filter(Device.imei == device_in.imei).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El IMEI ya está registrado",
        )

    device = Device(
        client_id=client_id,
        imei=device_in.imei,
        brand=device_in.brand,
        model=device_in.model,
        active=True,  # Default según el schema SQL
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return device
