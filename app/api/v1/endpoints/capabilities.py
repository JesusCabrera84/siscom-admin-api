"""
Endpoints de Capabilities.

Permite a las organizaciones:
- Ver sus capabilities efectivas
- Validar límites antes de operaciones

Las capabilities se resuelven con la regla:
    organization_override ?? plan_capability ?? default
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.schemas.capability import (
    CapabilitiesSummaryOut,
    ResolvedCapabilityOut,
    ValidateLimitRequest,
    ValidateLimitResponse,
)
from app.services.capabilities import CapabilityService

router = APIRouter()


@router.get("", response_model=CapabilitiesSummaryOut)
def get_capabilities_summary(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene el resumen de capabilities de la organización.

    Retorna:
    - limits: Capabilities de tipo límite (max_devices, max_users, etc.)
    - features: Capabilities de tipo feature (ai_features, analytics_tools, etc.)

    Cada valor se resuelve aplicando la regla:
    organization_override ?? plan_capability ?? default
    """
    summary = CapabilityService.get_capabilities_summary(db, organization_id)
    return CapabilitiesSummaryOut(**summary)


@router.get("/{capability_code}", response_model=ResolvedCapabilityOut)
def get_capability(
    capability_code: str,
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene el valor de una capability específica.

    Retorna:
    - code: Código de la capability
    - value: Valor resuelto
    - source: Fuente del valor (organization, plan, default)
    - expires_at: Si es un override temporal, fecha de expiración
    """
    resolved = CapabilityService.get_capability(db, organization_id, capability_code)

    return ResolvedCapabilityOut(
        code=resolved.code,
        value=resolved.value,
        source=resolved.source,
        plan_id=resolved.plan_id,
        expires_at=resolved.expires_at,
    )


@router.post("/validate-limit", response_model=ValidateLimitResponse)
def validate_limit(
    request: ValidateLimitRequest,
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    Valida si se puede agregar un elemento más sin exceder el límite.

    Útil para validar antes de crear:
    - Dispositivos (max_devices)
    - Geocercas (max_geofences)
    - Usuarios (max_users)

    Ejemplo:
    ```json
    {
        "capability_code": "max_devices",
        "current_count": 8
    }
    ```

    Respuesta:
    ```json
    {
        "can_add": true,
        "current_count": 8,
        "limit": 10,
        "remaining": 2
    }
    ```
    """
    limit = CapabilityService.get_limit(db, organization_id, request.capability_code)
    can_add = CapabilityService.validate_limit(
        db, organization_id, request.capability_code, request.current_count
    )

    # Si el límite es 0 o negativo, es ilimitado
    if limit <= 0:
        remaining = -1  # Indicador de ilimitado
    else:
        remaining = max(0, limit - request.current_count)

    return ValidateLimitResponse(
        can_add=can_add,
        current_count=request.current_count,
        limit=limit,
        remaining=remaining,
    )


@router.get("/check/{capability_code}")
def check_capability(
    capability_code: str,
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    Verifica si una capability booleana está habilitada.

    Útil para verificar rápidamente si una feature está disponible.

    Ejemplo: GET /capabilities/check/ai_features

    Respuesta:
    ```json
    {
        "capability": "ai_features",
        "enabled": true
    }
    ```
    """
    enabled = CapabilityService.has_capability(db, organization_id, capability_code)

    return {
        "capability": capability_code,
        "enabled": enabled,
    }
