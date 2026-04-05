from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: UUID
    organization_id: UUID
    rule_id: Optional[UUID] = None
    unit_id: UUID
    source_type: str
    source_id: Optional[str] = None
    type: str
    payload: Optional[dict[str, Any]] = None
    occurred_at: datetime
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
