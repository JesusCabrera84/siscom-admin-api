from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.device import Device, DeviceEvent
from app.schemas.device import DeviceEventOut

router = APIRouter()


@router.get("/{device_id}", response_model=List[DeviceEventOut])
def get_device_events(
    device_id: str,
    db: Session = Depends(get_db),
):
    """
    Obtiene el historial completo de eventos de un dispositivo.
    
    Este endpoint es la bitácora administrativa (historial de movimientos).
    Muestra todas las acciones registradas sobre el dispositivo en orden cronológico.
    
    Returns:
        Lista de eventos ordenados del más reciente al más antiguo.
    """
    # Verificar que el dispositivo existe
    device = db.query(Device).filter(Device.device_id == device_id).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    
    # Obtener todos los eventos del dispositivo
    events = (
        db.query(DeviceEvent)
        .filter(DeviceEvent.device_id == device_id)
        .order_by(DeviceEvent.created_at.desc())
        .all()
    )
    
    return events

