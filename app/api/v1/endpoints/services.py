"""
⚠️ ENDPOINTS LEGACY - NO USAR EN CÓDIGO NUEVO ⚠️

Estos endpoints dependen del modelo DeviceService que es LEGACY.
El modelo actual de negocio usa Subscriptions a nivel de organización.

MIGRACIÓN FUTURA:
- Los device_services activos deberán convertirse en Subscriptions
- Estos endpoints serán eliminados cuando se complete la migración

Para código nuevo, usar:
- /subscriptions endpoints
- app.services.subscription_query
"""

import warnings
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.device import Device
from app.models.device_service import DeviceService, DeviceServiceStatus
from app.models.plan import Plan
from app.schemas.device_service import (
    DeviceServiceConfirmPayment,
    DeviceServiceCreate,
    DeviceServiceOut,
)
from app.services.billing import cancel_device_service, confirm_payment
from app.services.device_activation import activate_device_service

router = APIRouter()

# Emitir warning al importar este módulo
warnings.warn(
    "Los endpoints /services son LEGACY. "
    "Para código nuevo, usar /subscriptions.",
    DeprecationWarning,
    stacklevel=2
)


@router.post(
    "/activate", response_model=DeviceServiceOut, status_code=status.HTTP_201_CREATED
)
def activate_service(
    service_in: DeviceServiceCreate,
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    ⚠️ LEGACY ⚠️ - Activa un servicio para un dispositivo.

    - Valida ownership del dispositivo
    - Verifica que no exista otro servicio ACTIVE
    - Crea payment y device_service
    - Actualiza device.active = True
    """
    device_service = activate_device_service(
        db=db,
        client_id=organization_id,  # Mantiene nombre de parámetro por compatibilidad con servicio
        device_id=service_in.device_id,
        plan_id=service_in.plan_id,
        subscription_type=service_in.subscription_type.value,
        simulate_immediate_payment=True,
    )

    return device_service


@router.post("/confirm-payment", response_model=dict)
def confirm_service_payment(
    payment_confirm: DeviceServiceConfirmPayment,
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    ⚠️ LEGACY ⚠️ - Confirma el pago de un servicio de dispositivo.
    Actualiza el payment a SUCCESS y activa el servicio si estaba pendiente.
    """
    # Verificar que el servicio pertenece a la organización
    device_service = (
        db.query(DeviceService)
        .filter(
            DeviceService.id == payment_confirm.device_service_id,
            DeviceService.client_id == organization_id,  # Mantiene client_id en DeviceService por ser LEGACY
        )
        .first()
    )

    if not device_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado o no pertenece a la organización",
        )

    payment = confirm_payment(
        db=db,
        payment_id=payment_confirm.payment_id,
        device_service_id=payment_confirm.device_service_id,
    )

    return {
        "message": "Pago confirmado exitosamente",
        "payment_id": str(payment.id),
        "status": payment.status,
    }


@router.get("/active", response_model=List[dict])
def list_active_services(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    ⚠️ LEGACY ⚠️ - Lista todos los servicios activos de la organización.
    Incluye información del dispositivo y plan asociados.
    """
    services = (
        db.query(
            DeviceService,
            Device.device_id,
            Device.brand,
            Device.model,
            Plan.name.label("plan_name"),
        )
        .join(Device, DeviceService.device_id == Device.device_id)
        .join(Plan, DeviceService.plan_id == Plan.id)
        .filter(
            DeviceService.client_id == organization_id,  # Mantiene client_id en DeviceService por ser LEGACY
            DeviceService.status == DeviceServiceStatus.ACTIVE.value,
        )
        .all()
    )

    result = []
    for service, device_id, brand, model, plan_name in services:
        service_dict = {
            "id": str(service.id),
            "device_id": str(service.device_id),
            "plan_id": str(service.plan_id),
            "subscription_type": service.subscription_type,
            "status": service.status,
            "activated_at": (
                service.activated_at.isoformat() if service.activated_at else None
            ),
            "expires_at": (
                service.expires_at.isoformat() if service.expires_at else None
            ),
            "auto_renew": service.auto_renew,
            "device_device_id": device_id,
            "device_brand": brand,
            "device_model": model,
            "plan_name": plan_name,
        }
        result.append(service_dict)

    return result


@router.patch("/{service_id}/cancel", response_model=DeviceServiceOut)
def cancel_service(
    service_id: UUID,
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    ⚠️ LEGACY ⚠️ - Cancela un servicio de dispositivo.
    Marca el servicio como CANCELLED y actualiza device.active si no hay otros activos.
    """
    device_service = cancel_device_service(
        db=db,
        device_service_id=service_id,
        client_id=organization_id,  # Mantiene nombre de parámetro por compatibilidad con servicio
    )

    return device_service
