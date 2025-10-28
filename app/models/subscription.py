from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship, Index
from sqlalchemy import Column, String, DateTime, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import enum

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.plan import Plan


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    TRIAL = "TRIAL"


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("idx_subscriptions_client", "client_id"),
        Index("idx_subscriptions_status", "status"),
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
    plan_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("plans.id"),
            nullable=False,
        ),
    )
    status: SubscriptionStatus = Field(
        sa_column=Column(
            String, default=SubscriptionStatus.ACTIVE.value, nullable=False
        )
    )
    started_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    cancelled_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    renewed_from: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True
        ),
    )
    auto_renew: bool = Field(sa_column=Column(Boolean, default=True, nullable=False))

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
    client: "Client" = Relationship(back_populates="subscriptions")
    plan: "Plan" = Relationship(back_populates="subscriptions")
