"""
Servicio de Planes y Validaciones de Suscripciones.

NOTA IMPORTANTE SOBRE LÓGICA LEGACY:
------------------------------------
La función `validate_device_limit_legacy` usa el campo `plan.max_devices` directamente.
Esta es lógica LEGACY que se mantiene por compatibilidad.

La forma CORRECTA de validar límites es usando CapabilityService:
    from app.services.capabilities import CapabilityService
    if not CapabilityService.validate_limit(db, client_id, "max_devices", current_count):
        raise HTTPException(403, "Límite de dispositivos alcanzado")

El sistema de capabilities permite:
- Overrides por organización (organization_capabilities)
- Valores por defecto del plan (plan_capabilities)
- Valores globales del sistema (DEFAULT_CAPABILITIES)
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.device_service import DeviceService, DeviceServiceStatus
from app.models.plan import Plan
from app.services.capabilities import CapabilityService


def get_plan_by_id(db: Session, plan_id: UUID) -> Plan:
    """
    Obtiene un plan por su ID.

    Args:
        db: Sesión de base de datos
        plan_id: ID del plan

    Returns:
        Plan encontrado

    Raises:
        HTTPException: Si el plan no existe
    """
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan no encontrado",
        )
    return plan


def get_all_plans(db: Session) -> list[Plan]:
    """
    Obtiene todos los planes disponibles.

    Args:
        db: Sesión de base de datos

    Returns:
        Lista de planes
    """
    return db.query(Plan).all()


def validate_device_limit(
    db: Session,
    client_id: UUID,
) -> bool:
    """
    Valida si la organización puede agregar más dispositivos.

    USA CapabilityService para respetar:
    - Overrides de organización
    - Valores del plan activo
    - Valores por defecto

    Args:
        db: Sesión de base de datos
        client_id: ID de la organización

    Returns:
        True si puede agregar dispositivos, False si no
    """
    active_count = get_active_services_count(db, client_id)
    return CapabilityService.validate_limit(db, client_id, "max_devices", active_count)


def validate_device_limit_legacy(
    db: Session,
    client_id: UUID,
    plan_id: UUID,
) -> bool:
    """
    LEGACY: Valida límite de dispositivos usando plan.max_devices directamente.

    ⚠️  DEPRECATED: Usar validate_device_limit() que usa CapabilityService.

    Esta función se mantiene por compatibilidad con código existente.
    NO debe usarse en código nuevo.

    Args:
        db: Sesión de base de datos
        client_id: ID del cliente
        plan_id: ID del plan

    Returns:
        True si puede agregar dispositivos, False si no
    """
    # Obtener el plan
    plan = get_plan_by_id(db, plan_id)

    # Si el plan no tiene límite (max_devices es None), siempre es válido
    if not hasattr(plan, "max_devices") or plan.max_devices is None:
        return True

    # Contar servicios activos del cliente
    active_count = get_active_services_count(db, client_id)

    # Validar contra el límite
    return active_count < plan.max_devices


def get_active_services_count(db: Session, client_id: UUID) -> int:
    """
    Cuenta la cantidad de servicios activos de una organización.

    Args:
        db: Sesión de base de datos
        client_id: ID de la organización

    Returns:
        Cantidad de servicios activos
    """
    return (
        db.query(DeviceService)
        .filter(
            DeviceService.client_id == client_id,
            DeviceService.status == DeviceServiceStatus.ACTIVE.value,
        )
        .count()
    )
