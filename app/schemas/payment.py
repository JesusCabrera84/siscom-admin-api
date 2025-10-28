from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from decimal import Decimal
from app.models.payment import PaymentStatus


class PaymentBase(BaseModel):
    amount: Decimal
    currency: str = "MXN"
    method: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentOut(PaymentBase):
    id: UUID
    client_id: UUID
    paid_at: Optional[datetime] = None
    status: PaymentStatus
    transaction_ref: Optional[str] = None
    invoice_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "client_id": "223e4567-e89b-12d3-a456-426614174000",
                "amount": "299.00",
                "currency": "MXN",
                "method": "card",
                "paid_at": "2024-01-15T10:30:00Z",
                "status": "SUCCESS",
                "transaction_ref": "txn_abc123xyz",
                "invoice_url": "https://example.com/invoices/123.pdf",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
