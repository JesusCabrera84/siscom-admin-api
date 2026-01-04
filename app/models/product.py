"""
Modelo de Product.

Los productos representan items que pueden incluirse en planes.
Ejemplos: GPS Tracker, Dashcam, Sensor de combustible, etc.

Tabla: products
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    """
    Modelo de producto (tabla: products).

    Representa un producto que puede estar incluido en un plan.
    Los productos se asocian a planes mediante plan_products.
    """

    __tablename__ = "products"

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )

    code: str = Field(
        sa_column=Column(Text, unique=True, nullable=False),
        description="Código único del producto (ej: 'gps_tracker', 'dashcam')",
    )

    name: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Nombre del producto",
    )

    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, default=True, nullable=True),
    )

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=True,
        ),
    )


class PlanProduct(SQLModel, table=True):
    """
    Relación entre planes y productos (tabla: plan_products).

    Define qué productos están incluidos en cada plan.
    """

    __tablename__ = "plan_products"

    plan_id: UUID = Field(
        primary_key=True,
        foreign_key="plans.id",
    )

    product_id: UUID = Field(
        primary_key=True,
        foreign_key="products.id",
    )
