from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_full
from app.db.session import get_db
from app.models.geofence import Geofence, GeofenceCell
from app.models.user import User
from app.schemas.geofence import (
    GeofenceCreate,
    GeofenceDeleteOut,
    GeofenceOut,
    GeofenceUpdate,
)

router = APIRouter()


def _unique_h3_indexes(h3_indexes: list[int]) -> list[int]:
    return list(dict.fromkeys(h3_indexes))


def _build_geofence_out(db: Session, geofence: Geofence) -> GeofenceOut:
    rows = (
        db.query(GeofenceCell.h3_index)
        .filter(GeofenceCell.geofence_id == geofence.id)
        .order_by(GeofenceCell.h3_index.asc())
        .all()
    )

    return GeofenceOut(
        id=geofence.id,
        organization_id=geofence.organization_id,
        created_by=geofence.created_by,
        name=geofence.name,
        description=geofence.description,
        config=geofence.config,
        h3_indexes=[row.h3_index for row in rows],
        is_active=geofence.is_active,
        created_at=geofence.created_at,
        updated_at=geofence.updated_at,
    )


def _get_active_geofence_or_404(
    db: Session, geofence_id: UUID, organization_id: UUID
) -> Geofence:
    geofence = (
        db.query(Geofence)
        .filter(
            Geofence.id == geofence_id,
            Geofence.organization_id == organization_id,
            Geofence.is_active.is_(True),
        )
        .first()
    )

    if not geofence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geocerca no encontrada",
        )

    return geofence


@router.post("", response_model=GeofenceOut, status_code=status.HTTP_201_CREATED)
def create_geofence(
    payload: GeofenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    geofence = Geofence(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        name=payload.name,
        description=payload.description,
        config=payload.config,
        is_active=True,
    )

    try:
        db.add(geofence)
        db.flush()

        for h3_index in _unique_h3_indexes(payload.h3_indexes):
            db.add(GeofenceCell(geofence_id=geofence.id, h3_index=h3_index))

        db.commit()
        db.refresh(geofence)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear la geocerca por conflicto de integridad",
        )

    return _build_geofence_out(db, geofence)


@router.get("", response_model=list[GeofenceOut])
def list_geofences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    geofences = (
        db.query(Geofence)
        .filter(
            Geofence.organization_id == current_user.organization_id,
            Geofence.is_active.is_(True),
        )
        .order_by(Geofence.created_at.desc())
        .all()
    )

    return [_build_geofence_out(db, geofence) for geofence in geofences]


@router.get("/{geofence_id}", response_model=GeofenceOut)
def get_geofence(
    geofence_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    geofence = _get_active_geofence_or_404(
        db, geofence_id, current_user.organization_id
    )
    return _build_geofence_out(db, geofence)


@router.patch("/{geofence_id}", response_model=GeofenceOut)
def update_geofence(
    geofence_id: UUID,
    payload: GeofenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    geofence = _get_active_geofence_or_404(
        db, geofence_id, current_user.organization_id
    )

    update_data = payload.model_dump(exclude_unset=True)
    h3_indexes = update_data.pop("h3_indexes", None)

    for field, value in update_data.items():
        setattr(geofence, field, value)

    try:
        if h3_indexes is not None:
            db.query(GeofenceCell).filter(
                GeofenceCell.geofence_id == geofence.id
            ).delete(synchronize_session=False)
            for h3_index in _unique_h3_indexes(h3_indexes):
                db.add(GeofenceCell(geofence_id=geofence.id, h3_index=h3_index))

        geofence.updated_at = datetime.utcnow()
        db.add(geofence)
        db.commit()
        db.refresh(geofence)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo actualizar la geocerca por conflicto de integridad",
        )

    return _build_geofence_out(db, geofence)


@router.delete("/{geofence_id}", response_model=GeofenceDeleteOut)
def delete_geofence(
    geofence_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    geofence = _get_active_geofence_or_404(
        db, geofence_id, current_user.organization_id
    )

    geofence.is_active = False
    geofence.updated_at = datetime.utcnow()

    db.add(geofence)
    db.commit()

    return GeofenceDeleteOut(
        message="Geocerca desactivada exitosamente",
        geofence_id=geofence.id,
        is_active=False,
    )
