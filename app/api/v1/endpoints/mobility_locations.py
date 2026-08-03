from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_full, get_mobility_kafka_producer
from app.db.session import get_db
from app.models.mobility_device import MobilityDevice
from app.models.user import User
from app.schemas.mobility_location import (
    MobilityLocationBatchIn,
    MobilityLocationBatchItemOut,
    MobilityLocationBatchOut,
    MobilityLocationIn,
    MobilityLocationOut,
    MobilityLocationPayload,
    to_utc_iso_z,
)
from app.services.messaging.kafka_producer import MobilityKafkaProducer

router = APIRouter()


def _require_own_active_device(
    db: Session, device_id: UUID, current_user: User
) -> MobilityDevice:
    """
    Valida que el dispositivo exista, pertenezca al usuario autenticado y esté
    activo antes de aceptar ubicaciones suyas.

    Se responde 404 tanto si no existe como si es de otro usuario, para no
    convertir el endpoint en un oráculo de device_id válidos.
    """
    device = (
        db.query(MobilityDevice)
        .filter(
            MobilityDevice.id == device_id,
            MobilityDevice.user_id == current_user.id,
        )
        .first()
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="device_id no existe o no pertenece al usuario.",
        )
    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El dispositivo está desactivado y no puede publicar ubicaciones.",
        )
    return device


def _build_message(
    *,
    device_id: str,
    payload: MobilityLocationPayload,
    received_at: datetime,
) -> dict:
    return {
        "device_id": device_id,
        "recorded_at": to_utc_iso_z(payload.recorded_at),
        "received_at": to_utc_iso_z(received_at),
        "lat": payload.lat,
        "lon": payload.lon,
        "accuracy_m": payload.accuracy_m,
        "speed_mps": payload.speed_mps,
        "heading": payload.heading,
        "altitude_m": payload.altitude_m,
        "battery_level": payload.battery_level,
        "motion_state": payload.motion_state,
        "h3_index": payload.h3_index,
        "h3_resolution": payload.h3_resolution,
    }


@router.post(
    "", response_model=MobilityLocationOut, status_code=status.HTTP_202_ACCEPTED
)
def publish_mobility_location(
    payload: MobilityLocationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
    mobility_kafka_producer: MobilityKafkaProducer = Depends(
        get_mobility_kafka_producer
    ),
):
    """Valida y publica una ubicación de movilidad enriquecida con received_at."""
    _require_own_active_device(db, payload.device_id, current_user)

    received_at = datetime.now(timezone.utc)
    message = _build_message(
        device_id=str(payload.device_id),
        payload=payload,
        received_at=received_at,
    )

    published = mobility_kafka_producer.publish_location(
        payload=message,
        key=str(payload.device_id),
    )
    if not published:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible publicar la ubicación en Kafka.",
        )

    return MobilityLocationOut(**message)


@router.post(
    "/batch",
    response_model=MobilityLocationBatchOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def publish_mobility_locations_batch(
    payload: MobilityLocationBatchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
    mobility_kafka_producer: MobilityKafkaProducer = Depends(
        get_mobility_kafka_producer
    ),
):
    """Valida y publica un batch de ubicaciones enriquecidas con received_at."""
    _require_own_active_device(db, payload.device_id, current_user)

    device_id = str(payload.device_id)
    published_locations: list[MobilityLocationBatchItemOut] = []

    for location in payload.locations:
        received_at = datetime.now(timezone.utc)
        message = _build_message(
            device_id=device_id,
            payload=location,
            received_at=received_at,
        )

        published = mobility_kafka_producer.publish_location(
            payload=message,
            key=device_id,
        )
        if not published:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No fue posible publicar la ubicación en Kafka.",
            )

        published_locations.append(
            MobilityLocationBatchItemOut(
                recorded_at=message["recorded_at"],
                received_at=message["received_at"],
                lat=message["lat"],
                lon=message["lon"],
                accuracy_m=message["accuracy_m"],
                speed_mps=message["speed_mps"],
                heading=message["heading"],
                altitude_m=message["altitude_m"],
                battery_level=message["battery_level"],
                motion_state=message["motion_state"],
                h3_index=message["h3_index"],
                h3_resolution=message["h3_resolution"],
            )
        )

    return MobilityLocationBatchOut(
        device_id=payload.device_id,
        locations=published_locations,
    )
