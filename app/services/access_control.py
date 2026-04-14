from uuid import UUID

from sqlalchemy.orm import Session

from app.models.unit import Unit
from app.models.user import User
from app.models.user_unit import UserUnit


def get_accessible_unit_ids(db: Session, user: User) -> list[UUID]:
    """
    Retorna los IDs de unidades accesibles para el usuario.
    - Si es maestro: todas las unidades activas de la organización
    - Si no es maestro: solo las unidades activas asignadas en user_units
    """
    if user.is_master:
        unit_ids = (
            db.query(Unit.id)
            .filter(
                Unit.organization_id == user.organization_id,
                Unit.deleted_at.is_(None),
            )
            .all()
        )
    else:
        unit_ids = (
            db.query(UserUnit.unit_id)
            .filter(UserUnit.user_id == user.id)
            .join(Unit, Unit.id == UserUnit.unit_id)
            .filter(
                Unit.organization_id == user.organization_id,
                Unit.deleted_at.is_(None),
            )
            .all()
        )

    return [unit_id[0] for unit_id in unit_ids]
