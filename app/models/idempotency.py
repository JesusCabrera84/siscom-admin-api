# app/models/idempotency.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Index, SQLModel

IDEMPOTENCY_TTL = timedelta(hours=24)
IDEMPOTENCY_IN_PROGRESS = "in_progress"
IDEMPOTENCY_COMPLETED = "completed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_expires_at() -> datetime:
    return _utcnow() + IDEMPOTENCY_TTL


class ApiIdempotencyRequest(SQLModel, table=True):
    """
    Reserva HTTP de idempotencia (capa cliente → API).
    Independiente de payments.idempotency_key (capa API → Stripe).
    """

    __tablename__ = "api_idempotency_requests"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            "account_id",
            "endpoint",
            name="uq_idem_account_endpoint",
        ),
        Index("idx_idem_expires", "expires_at"),
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True),
    )
    idempotency_key: str = Field(sa_column=Column(Text, nullable=False))
    account_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("accounts.id"),
            nullable=False,
        )
    )
    endpoint: str = Field(sa_column=Column(Text, nullable=False))
    request_hash: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(sa_column=Column(Text, nullable=False))
    status_code: Optional[int] = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    response_body: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    expires_at: datetime = Field(
        default_factory=_default_expires_at,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
