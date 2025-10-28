from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_client_id
from app.models.payment import Payment
from app.schemas.payment import PaymentOut

router = APIRouter()


@router.get("/", response_model=List[PaymentOut])
def list_payments(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """
    Lista los pagos del cliente autenticado.
    Soporta paginación con limit y offset.
    """
    payments = (
        db.query(Payment)
        .filter(Payment.client_id == client_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return payments
