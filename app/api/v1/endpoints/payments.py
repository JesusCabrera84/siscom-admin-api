"""
Endpoints de pagos.

Gestiona la consulta de pagos asociados a organizaciones.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.payment import Payment
from app.schemas.payment import PaymentOut

router = APIRouter()


@router.get("", response_model=List[PaymentOut])
def list_payments(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """
    Lista los pagos de la organización autenticada.
    Soporta paginación con limit y offset.
    """
    payments = (
        db.query(Payment)
        .filter(Payment.client_id == organization_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return payments
