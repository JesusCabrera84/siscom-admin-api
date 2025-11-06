import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Index, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.order_item import OrderItem
    from app.models.payment import Payment


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_orders_client", "client_id"),
        Index("idx_orders_status", "status"),
    )

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    client_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("clients.id"),
            nullable=False,
        ),
    )
    total_amount: Decimal = Field(sa_column=Column(String, nullable=False))
    status: OrderStatus = Field(
        sa_column=Column(String, default=OrderStatus.PENDING.value, nullable=False)
    )
    payment_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), ForeignKey("payments.id"), nullable=True
        ),
    )
    shipped_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )

    # Relationships
    client: "Client" = Relationship(back_populates="orders")
    payment: Optional["Payment"] = Relationship(back_populates="orders")
    order_items: list["OrderItem"] = Relationship(back_populates="order")
