"""
Schemas para Suscripciones.

Define los schemas de entrada/salida para el sistema de suscripciones.

MODELO CONCEPTUAL:
==================
Las suscripciones pertenecen a ORGANIZATIONS (raíz operativa).
Los pagos pertenecen a ACCOUNTS (raíz comercial).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.subscription import BillingCycle, SubscriptionStatus


class SubscriptionBase(BaseModel):
    """Base para una suscripción."""
    plan_id: UUID = Field(..., description="ID del plan")
    billing_cycle: BillingCycle = Field(
        default=BillingCycle.MONTHLY,
        description="Ciclo de facturación"
    )
    auto_renew: bool = Field(default=True, description="Renovación automática")


class SubscriptionCreate(SubscriptionBase):
    """Schema para crear una suscripción."""
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "123e4567-e89b-12d3-a456-426614174000",
                "billing_cycle": "MONTHLY",
                "auto_renew": True,
            }
        }


class SubscriptionOut(BaseModel):
    """Suscripción en respuestas."""
    id: UUID
    organization_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    billing_cycle: Optional[str] = None
    started_at: datetime
    expires_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    renewed_from: Optional[UUID] = None
    auto_renew: bool = True
    external_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Alias de compatibilidad (DEPRECATED)
    @property
    def client_id(self) -> UUID:
        """DEPRECATED: Usar organization_id"""
        return self.organization_id

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "223e4567-e89b-12d3-a456-426614174000",
                "plan_id": "323e4567-e89b-12d3-a456-426614174000",
                "status": "ACTIVE",
                "billing_cycle": "MONTHLY",
                "started_at": "2024-01-01T00:00:00Z",
                "expires_at": "2024-02-01T00:00:00Z",
                "cancelled_at": None,
                "renewed_from": None,
                "auto_renew": True,
                "external_id": "sub_1234567890",
                "current_period_start": "2024-01-01T00:00:00Z",
                "current_period_end": "2024-02-01T00:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class SubscriptionWithPlanOut(SubscriptionOut):
    """Suscripción con información del plan."""
    plan_name: Optional[str] = None
    plan_code: Optional[str] = None
    days_remaining: Optional[int] = None
    is_active: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "223e4567-e89b-12d3-a456-426614174000",
                "plan_id": "323e4567-e89b-12d3-a456-426614174000",
                "status": "ACTIVE",
                "billing_cycle": "MONTHLY",
                "started_at": "2024-01-01T00:00:00Z",
                "expires_at": "2024-02-01T00:00:00Z",
                "auto_renew": True,
                "plan_name": "Plan Profesional",
                "plan_code": "pro",
                "days_remaining": 15,
                "is_active": True,
            }
        }


class SubscriptionCancelRequest(BaseModel):
    """Request para cancelar una suscripción."""
    reason: Optional[str] = Field(None, max_length=500, description="Razón de cancelación")
    cancel_immediately: bool = Field(
        default=False,
        description="Si es True, cancela inmediatamente. Si es False, cancela al final del período."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Ya no necesito el servicio",
                "cancel_immediately": False,
            }
        }


class SubscriptionRenewRequest(BaseModel):
    """Request para renovar una suscripción."""
    new_plan_id: Optional[UUID] = Field(None, description="ID del nuevo plan (para upgrade/downgrade)")
    billing_cycle: Optional[BillingCycle] = Field(None, description="Nuevo ciclo de facturación")

    class Config:
        json_schema_extra = {
            "example": {
                "new_plan_id": "423e4567-e89b-12d3-a456-426614174000",
                "billing_cycle": "YEARLY",
            }
        }


class SubscriptionsListOut(BaseModel):
    """Lista de suscripciones."""
    subscriptions: list[SubscriptionWithPlanOut]
    active_count: int = 0
    total_count: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "subscriptions": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "organization_id": "223e4567-e89b-12d3-a456-426614174000",
                        "plan_id": "323e4567-e89b-12d3-a456-426614174000",
                        "status": "ACTIVE",
                        "plan_name": "Plan Profesional",
                        "is_active": True,
                    }
                ],
                "active_count": 1,
                "total_count": 3,
            }
        }
