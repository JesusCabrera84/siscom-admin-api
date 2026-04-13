import logging
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_full
from app.db.session import get_db
from app.models.user import User
from app.models.user_device import UserDevice
from app.schemas.user_device import (
    DeviceDeactivateIn,
    DeviceDeactivateOut,
    DeviceRegisterIn,
    DeviceRegisterOut,
)
from app.services.sns import get_or_recreate_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=DeviceRegisterOut)
def register_user_device(
    payload: DeviceRegisterIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    now = datetime.now(timezone.utc)
    device = (
        db.query(UserDevice)
        .filter(UserDevice.device_token == payload.device_token)
        .first()
    )

    try:
        if not device:
            endpoint_arn, _ = get_or_recreate_endpoint(
                device_token=payload.device_token,
                platform=payload.platform,
                endpoint_arn=None,
            )
            device = UserDevice(
                user_id=current_user.id,
                device_token=payload.device_token,
                platform=payload.platform,
                endpoint_arn=endpoint_arn,
                is_active=True,
                last_seen_at=now,
                updated_at=now,
            )
            db.add(device)
            db.commit()
            db.refresh(device)

            return DeviceRegisterOut(
                device_token=device.device_token,
                platform=device.platform,
                endpoint_arn=device.endpoint_arn,
                is_active=device.is_active,
                last_seen_at=device.last_seen_at,
            )

        endpoint_arn, recreated = get_or_recreate_endpoint(
            device_token=payload.device_token,
            platform=payload.platform,
            endpoint_arn=device.endpoint_arn,
        )

        device.user_id = current_user.id
        device.platform = payload.platform
        device.is_active = True
        device.last_seen_at = now
        device.updated_at = now

        if recreated or not device.endpoint_arn:
            device.endpoint_arn = endpoint_arn

        db.add(device)
        db.commit()
        db.refresh(device)

        return DeviceRegisterOut(
            device_token=device.device_token,
            platform=device.platform,
            endpoint_arn=device.endpoint_arn,
            is_active=device.is_active,
            last_seen_at=device.last_seen_at,
        )
    except (ValueError, RuntimeError, ClientError, BotoCoreError) as exc:
        logger.exception("Error registrando dispositivo en SNS")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible registrar el dispositivo en SNS. "
                "Verifica AWS_REGION y los ARN de plataforma SNS."
            ),
        ) from exc


@router.post("/deactivate", response_model=DeviceDeactivateOut)
def deactivate_user_device(
    payload: DeviceDeactivateIn,
    db: Session = Depends(get_db),
):
    device = (
        db.query(UserDevice)
        .filter(UserDevice.device_token == payload.device_token)
        .first()
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )

    device.is_active = False
    device.updated_at = datetime.now(timezone.utc)

    db.add(device)
    db.commit()

    return DeviceDeactivateOut(
        message="Dispositivo desactivado exitosamente",
        device_token=payload.device_token,
        is_active=False,
    )
