from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship, Index
from sqlalchemy import Column, String, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from decimal import Decimal
import enum

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.order import Order


class PaymentStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PENDING = "PENDING"


class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    __table_args__ = (
        Index("idx_payments_client", "client_id"),
        Index("idx_payments_status", "status"),
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
    amount: Decimal = Field(sa_column=Column(String, nullable=False))
    currency: str = Field(max_length=10, default="MXN", nullable=False)
    method: Optional[str] = Field(default=None, max_length=50)
    paid_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    status: PaymentStatus = Field(
        sa_column=Column(String, default=PaymentStatus.PENDING.value, nullable=False)
    )
    transaction_ref: Optional[str] = Field(default=None, max_length=255)
    invoice_url: Optional[str] = Field(default=None, max_length=500)

    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )

    # Relationships
    client: "Client" = Relationship(back_populates="payments")
    orders: list["Order"] = Relationship(back_populates="payment")
