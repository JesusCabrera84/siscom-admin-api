from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship, Index
from sqlalchemy import Column, String, DateTime, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID

if TYPE_CHECKING:
    from app.models.client import Client


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_cognito_sub", "cognito_sub"),
        Index("idx_users_client_master", "client_id", "is_master"),
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
    cognito_sub: str = Field(
        sa_column=Column(String(255), unique=True, nullable=False, index=True)
    )
    email: str = Field(max_length=255, nullable=False)
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_master: bool = Field(sa_column=Column(Boolean, default=False, nullable=False))
    last_login_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
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
    client: "Client" = Relationship(back_populates="users")
