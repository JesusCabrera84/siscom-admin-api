"""
Schemas de compatibilidad para Clients.

DEPRECATED: Este módulo existe solo para compatibilidad hacia atrás.
Usar los schemas de app.schemas.account en su lugar.

MIGRACIÓN:
==========
- OnboardingRequest -> app.schemas.account.OnboardingRequest
- OnboardingResponse -> app.schemas.account.OnboardingResponse
- ClientOut -> app.schemas.account.OrganizationOut
"""

from pydantic import BaseModel

from app.models.organization import OrganizationStatus

# Re-exportar schemas para compatibilidad
from app.schemas.account import (
    OnboardingRequest,
    OnboardingResponse,
)
from app.schemas.organization import OrganizationOut


# Schema legacy para compatibilidad (DEPRECATED)
class ClientBase(BaseModel):
    """Base para un cliente/organización. DEPRECATED: Usar OrganizationOut."""

    name: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE


# Aliases de compatibilidad (DEPRECATED)
ClientOut = OrganizationOut
ClientCreate = OnboardingRequest
OrganizationCreate = OnboardingRequest

__all__ = [
    "OnboardingRequest",
    "OnboardingResponse",
    "OrganizationOut",
    "ClientBase",
    "ClientOut",
    "ClientCreate",
    "OrganizationCreate",
]
