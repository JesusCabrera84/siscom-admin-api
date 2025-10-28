from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.models.device_service import SubscriptionType, DeviceServiceStatus


class DeviceServiceCreate(BaseModel):
    device_id: UUID
    plan_id: UUID
    subscription_type: SubscriptionType

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "plan_id": "223e4567-e89b-12d3-a456-426614174000",
                "subscription_type": "MONTHLY",
            }
        }


class DeviceServiceOut(BaseModel):
    id: UUID
    device_id: UUID
    client_id: UUID
    plan_id: UUID
    subscription_id: Optional[UUID] = None
    subscription_type: SubscriptionType
    status: DeviceServiceStatus
    activated_at: datetime
    expires_at: Optional[datetime] = None
    renewed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    auto_renew: bool
    payment_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "device_id": "223e4567-e89b-12d3-a456-426614174000",
                "client_id": "323e4567-e89b-12d3-a456-426614174000",
                "plan_id": "423e4567-e89b-12d3-a456-426614174000",
                "subscription_id": None,
                "subscription_type": "MONTHLY",
                "status": "ACTIVE",
                "activated_at": "2024-01-15T10:30:00Z",
                "expires_at": "2024-02-14T10:30:00Z",
                "renewed_at": None,
                "cancelled_at": None,
                "auto_renew": True,
                "payment_id": "523e4567-e89b-12d3-a456-426614174000",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class DeviceServiceConfirmPayment(BaseModel):
    device_service_id: UUID
    payment_id: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "device_service_id": "123e4567-e89b-12d3-a456-426614174000",
                "payment_id": "223e4567-e89b-12d3-a456-426614174000",
            }
        }


class DeviceServiceWithDetails(DeviceServiceOut):
    """
    Schema extendido que incluye detalles del dispositivo y plan.
    Útil para endpoints que retornan servicios con info completa.
    """

    device_imei: Optional[str] = None
    device_brand: Optional[str] = None
    plan_name: Optional[str] = None

    class Config:
        from_attributes = True
