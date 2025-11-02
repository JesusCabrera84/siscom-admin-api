from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import enum

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.device import Device
    from app.models.subscription import Subscription
    from app.models.payment import Payment
    from app.models.order import Order


class ClientStatus(str, enum.Enum):
    PENDING = "PENDING"  # Cliente pendiente de verificación de email
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class Client(SQLModel, table=True):
    __tablename__ = "clients"

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    name: str = Field(max_length=255, nullable=False)
    status: ClientStatus = Field(
        sa_column=Column(String, default=ClientStatus.PENDING.value, nullable=False)
    )
    active_subscription_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True
        ),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
        )
    )

    # Relationships
    users: list["User"] = Relationship(back_populates="client")
    devices: list["Device"] = Relationship(back_populates="client")
    subscriptions: list["Subscription"] = Relationship(
        back_populates="client",
        sa_relationship_kwargs={"foreign_keys": "[Subscription.client_id]"},
    )
    active_subscription: Optional["Subscription"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Client.active_subscription_id]",
            "uselist": False,
        }
    )
    payments: list["Payment"] = Relationship(back_populates="client")
    orders: list["Order"] = Relationship(back_populates="client")
