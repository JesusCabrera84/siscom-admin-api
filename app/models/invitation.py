from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, String, DateTime, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class Invitation(SQLModel, table=True):
    __tablename__ = "invitations"

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
    invited_email: str = Field(max_length=255, nullable=False)
    invited_by_user_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=False,
        ),
    )
    token: str = Field(
        sa_column=Column(String(255), unique=True, nullable=False, index=True)
    )
    expires_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    accepted: bool = Field(sa_column=Column(Boolean, default=False, nullable=False))

    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
