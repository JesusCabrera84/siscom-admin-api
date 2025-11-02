from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, DateTime, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, TIMESTAMP
import enum

if TYPE_CHECKING:
    from app.models.user import User


class TokenType(str, enum.Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class TokenConfirmacion(SQLModel, table=True):
    __tablename__ = "tokens_confirmacion"

    id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    token: str = Field(
        sa_column=Column(String, unique=True, nullable=False, index=True)
    )
    expires_at: datetime = Field(
        sa_column=Column(
            DateTime,
            default=lambda: datetime.utcnow() + timedelta(hours=1),
            nullable=False,
        )
    )
    used: bool = Field(sa_column=Column(Boolean, default=False, nullable=False))
    type: TokenType = Field(
        sa_column=Column(
            String, default=TokenType.EMAIL_VERIFICATION.value, nullable=False
        )
    )
    user_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True), 
            server_default=text("NOW()"), 
            nullable=False
        )
    )

    # Relationships
    user: "User" = Relationship(back_populates="tokens")

