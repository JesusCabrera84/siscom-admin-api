from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.plan import Plan
from app.models.device_service import DeviceService, DeviceServiceStatus


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
    plan_id: UUID,
) -> bool:
    """
    Valida si el cliente puede agregar más dispositivos según el límite del plan.
    Por ahora es un stub que siempre retorna True.

    En el futuro, podría implementarse verificando:
    - Cantidad de device_services activos del cliente
    - max_devices del plan

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
    if plan.max_devices is None:
        return True

    # Contar servicios activos del cliente
    active_count = (
        db.query(DeviceService)
        .filter(
            DeviceService.client_id == client_id,
            DeviceService.status == DeviceServiceStatus.ACTIVE.value,
        )
        .count()
    )

    # Validar contra el límite
    return active_count < plan.max_devices


def get_active_services_count(db: Session, client_id: UUID) -> int:
    """
    Cuenta la cantidad de servicios activos de un cliente.

    Args:
        db: Sesión de base de datos
        client_id: ID del cliente

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
