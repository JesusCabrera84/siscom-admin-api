"""Perfil fiscal SAT de una cuenta (RFC, régimen, domicilio mínimo)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class AccountTaxProfile(SQLModel, table=True):
    __tablename__ = "account_tax_profiles"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_account_tax_profiles_account"),
    )

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa_text("gen_random_uuid()"),
        )
    )
    account_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("accounts.id"),
            nullable=False,
        )
    )
    rfc: str = Field(sa_column=Column(Text, nullable=False))
    legal_name: str = Field(sa_column=Column(Text, nullable=False))
    tax_system: str = Field(sa_column=Column(Text, nullable=False))
    zip: str = Field(sa_column=Column(Text, nullable=False))
    email: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    default_cfdi_use: str = Field(
        default="G03",
        sa_column=Column(Text, nullable=False, server_default="G03"),
    )
    facturapi_customer_id: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    facturapi_livemode: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=sa_text("false")),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=sa_text("now()")
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=sa_text("now()")
        )
    )
