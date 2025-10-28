from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from decimal import Decimal
from app.models.order import OrderStatus
from app.models.order_item import OrderItemType


class OrderItemCreate(BaseModel):
    item_type: OrderItemType
    device_id: Optional[UUID] = None
    description: str
    quantity: int = 1
    unit_price: Decimal

    class Config:
        json_schema_extra = {
            "example": {
                "item_type": "DEVICE",
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Dispositivo GPS Queclink GV300",
                "quantity": 2,
                "unit_price": "1500.00",
            }
        }


class OrderItemOut(BaseModel):
    id: UUID
    order_id: UUID
    item_type: OrderItemType
    device_id: Optional[UUID] = None
    description: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "item_type": "DEVICE",
                        "description": "Dispositivo GPS Queclink GV300",
                        "quantity": 2,
                        "unit_price": "1500.00",
                    },
                    {
                        "item_type": "ACCESSORY",
                        "description": "Antena GPS externa",
                        "quantity": 2,
                        "unit_price": "200.00",
                    },
                ]
            }
        }


class OrderOut(BaseModel):
    id: UUID
    client_id: UUID
    total_amount: Decimal
    status: OrderStatus
    payment_id: Optional[UUID] = None
    shipped_at: Optional[datetime] = None
    created_at: datetime
    order_items: List[OrderItemOut] = []

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "client_id": "223e4567-e89b-12d3-a456-426614174000",
                "total_amount": "3400.00",
                "status": "PENDING",
                "payment_id": None,
                "shipped_at": None,
                "created_at": "2024-01-15T10:30:00Z",
                "order_items": [],
            }
        }
