"""
Endpoints de Planes - API Pública (Read-Only).

Los planes son INFORMATIVOS - muestran precios, capabilities y opciones disponibles.
NO gobiernan la lógica del sistema, eso lo hacen:
- Suscripciones: determinan qué plan tiene cada organización
- Capabilities: determinan qué puede hacer cada organización

IMPORTANTE:
- Esta API es de solo lectura
- Solo muestra planes activos
- No permite crear ni modificar planes
- Para gestión de planes, usar la API Internal (/internal/plans)

Estos endpoints son públicos para que el frontend pueda mostrar
el catálogo de planes sin requerir autenticación.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.capability import PlanCapability
from app.models.plan import Plan
from app.schemas.plan import (
    BillingCycle,
    PlanDetailOut,
    PlanPricing,
    PlansListOut,
)

router = APIRouter()


def _get_plan_capabilities(db: Session, plan_id: UUID) -> dict:
    """
    Obtiene las capabilities de un plan como diccionario.
    """
    plan_caps = db.query(PlanCapability).filter(PlanCapability.plan_id == plan_id).all()

    capabilities = {}
    for pc in plan_caps:
        if pc.capability:
            capabilities[pc.capability.code] = pc.get_value()

    return capabilities


def _generate_highlighted_features(capabilities: dict) -> list[str]:
    """
    Genera lista de features destacados basado en capabilities.
    """
    features = []

    if "max_devices" in capabilities:
        features.append(f"Hasta {capabilities['max_devices']} dispositivos")
    if "max_geofences" in capabilities:
        features.append(f"{capabilities['max_geofences']} geocercas")
    if "max_users" in capabilities:
        features.append(f"Hasta {capabilities['max_users']} usuarios")
    if "history_days" in capabilities:
        features.append(f"{capabilities['history_days']} días de historial")
    if capabilities.get("ai_features"):
        features.append("Funciones de IA incluidas")
    if capabilities.get("analytics_tools"):
        features.append("Herramientas de analytics")
    if capabilities.get("api_access"):
        features.append("Acceso a API")
    if capabilities.get("priority_support"):
        features.append("Soporte prioritario")

    return features


def _plan_to_detail(db: Session, plan: Plan) -> PlanDetailOut:
    """
    Convierte un Plan a PlanDetailOut con toda la información.
    """
    capabilities = _get_plan_capabilities(db, plan.id)

    # Calcular ahorro anual
    monthly_annual = float(plan.price_monthly) * 12
    yearly_price = float(plan.price_yearly)
    savings_percent = 0
    if monthly_annual > 0 and yearly_price < monthly_annual:
        savings_percent = int(((monthly_annual - yearly_price) / monthly_annual) * 100)

    return PlanDetailOut(
        id=plan.id,
        name=plan.name,
        code=plan.code,
        description=plan.description,
        pricing=PlanPricing(
            monthly=plan.price_monthly,
            yearly=plan.price_yearly,
            yearly_savings_percent=savings_percent,
        ),
        billing_cycles=[BillingCycle.MONTHLY, BillingCycle.YEARLY],
        capabilities=capabilities,
        highlighted_features=_generate_highlighted_features(capabilities),
        is_popular=(plan.code == "pro"),  # Marcar "pro" como popular por defecto
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("", response_model=PlansListOut)
def list_plans(
    db: Session = Depends(get_db),
):
    """
    Obtiene el catálogo de planes disponibles.

    Este endpoint NO requiere autenticación para permitir consultas públicas.
    Solo muestra planes activos.

    Returns:
        Lista de planes con sus precios, capabilities y opciones de facturación.

    Notas:
        - Los planes son INFORMATIVOS, no gobiernan la lógica
        - Para ver qué puede hacer una organización, usar /capabilities
        - Para ver suscripciones activas, usar /subscriptions
        - Para gestión de planes, usar la API Internal (/internal/plans)
    """
    plans = (
        db.query(Plan).filter(Plan.is_active).order_by(Plan.price_monthly.asc()).all()
    )

    plans_detail = [_plan_to_detail(db, plan) for plan in plans]

    return PlansListOut(plans=plans_detail, total=len(plans_detail))


@router.get("/{plan_identifier}", response_model=PlanDetailOut)
def get_plan(
    plan_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Obtiene un plan específico por ID o código.

    Args:
        plan_identifier: UUID del plan o código del plan (ej: "pro", "enterprise")

    Returns:
        Detalle completo del plan incluyendo capabilities y precios.

    Notas:
        - Este endpoint es público
        - Los planes son INFORMATIVOS, la lógica está en subscriptions y capabilities
    """
    # Intentar como UUID primero
    plan = None
    try:
        plan_uuid = UUID(plan_identifier)
        plan = db.query(Plan).filter(Plan.id == plan_uuid).first()
    except ValueError:
        # No es UUID, buscar por código
        plan = db.query(Plan).filter(Plan.code == plan_identifier).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_identifier}' no encontrado",
        )

    return _plan_to_detail(db, plan)
