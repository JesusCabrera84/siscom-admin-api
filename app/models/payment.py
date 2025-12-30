"""
Modelo de Payment.

Los pagos pertenecen a Account (no a Organization).
Esto es parte del modelo dual:
- Account = Raíz comercial (billing, facturación)
- Organization = Raíz operativa (permisos, uso diario)

Los pagos se registran a nivel de Account para permitir
facturación consolidada de múltiples organizaciones.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Index, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.order import Order


class PaymentStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PENDING = "PENDING"


class Payment(SQLModel, table=True):
    """
    Registro de pago.

    Pertenece a Account (entidad comercial/billing).
    """

    __tablename__ = "payments"
    __table_args__ = (
        Index("idx_payments_account", "account_id"),
        Index("idx_payments_status", "status"),
    )

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    account_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("accounts.id"),
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
    account: "Account" = Relationship(back_populates="payments")
    orders: list["Order"] = Relationship(back_populates="payment")

    # Alias para compatibilidad (DEPRECATED)
    # NOTA: client_id no aplica a Payment - usa account_id
    @property
    def client_id(self) -> UUID:
        """
        DEPRECATED: Payment pertenece a Account, no a Organization.
        Este property existe solo para compatibilidad temporal.
        """
        return self.account_id
