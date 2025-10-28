from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.subscriptions import get_all_plans
from app.schemas.plan import PlanOut

router = APIRouter()


@router.get("/", response_model=List[PlanOut])
def list_plans(
    db: Session = Depends(get_db),
):
    """
    Obtiene el catálogo de planes disponibles.
    Este endpoint no requiere autenticación para permitir consultas públicas.
    """
    plans = get_all_plans(db)
    return plans
