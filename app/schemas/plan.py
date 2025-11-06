from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price_monthly: Decimal
    price_yearly: Decimal
    max_devices: int = 1
    history_days: int = 7
    ai_features: bool = False
    analytics_tools: bool = False
    features: Optional[dict] = None


class PlanOut(PlanBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Plan Básico",
                "description": "Plan básico para rastreo GPS",
                "price_monthly": "299.00",
                "price_yearly": "2990.00",
                "max_devices": 10,
                "history_days": 30,
                "ai_features": False,
                "analytics_tools": False,
                "features": {
                    "real_time_tracking": True,
                    "alerts": True,
                    "reports": "basic",
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }
