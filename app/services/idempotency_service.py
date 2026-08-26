# app/services/idempotency_service.py
"""
Idempotencia HTTP: reserva atómica de (key, account, endpoint) ANTES de ejecutar.

No cachea 5xx: si el outcome es desconocido se abandona la reserva para que
el reintento pueda repetir la operación de forma segura.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.idempotency import (
    IDEMPOTENCY_COMPLETED,
    IDEMPOTENCY_IN_PROGRESS,
    IDEMPOTENCY_TTL,
    ApiIdempotencyRequest,
)

logger = logging.getLogger(__name__)

PAYMENT_INTENT_ENDPOINT = "payment-intent"
STALE_IN_PROGRESS_SECONDS = 30
_KEY_RE = re.compile(r"^[A-Za-z0-9._~:/=+\-]{8,255}$")


@dataclass(frozen=True)
class IdempotencyHit:
    status_code: int
    body: dict


@dataclass
class IdempotencyReservation:
    record_id: UUID
    cached: Optional[IdempotencyHit] = None


def canonical_request_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def validate_idempotency_key(key: str) -> str:
    if not key or not _KEY_RE.fullmatch(key):
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key inválida. Use 8-255 caracteres URL-safe.",
        )
    return key


def require_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> str:
    """Obligatoria en POST /payment-intent. 400 si falta o es inválida."""
    if idempotency_key is None or not idempotency_key.strip():
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key es obligatoria para crear un cobro.",
        )
    return validate_idempotency_key(idempotency_key.strip())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(ts: Optional[datetime]) -> Optional[datetime]:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def _is_expired(record: ApiIdempotencyRequest, now: datetime) -> bool:
    expires = _as_aware(record.expires_at)
    return expires is None or expires <= now


def _is_stale_in_progress(record: ApiIdempotencyRequest, now: datetime) -> bool:
    created = _as_aware(record.created_at) or now
    return (now - created).total_seconds() >= STALE_IN_PROGRESS_SECONDS


def begin_idempotency(
    db: Session,
    idempotency_key: str,
    account_id: UUID,
    endpoint: str,
    request_hash: str,
) -> IdempotencyReservation:
    """
    Inserta la reserva. Si la key ya existe, reusa la respuesta o rechaza.
    La reserva se COMMITEA antes de la operación de negocio.
    """
    key = validate_idempotency_key(idempotency_key)
    now = _utcnow()
    record = ApiIdempotencyRequest(
        idempotency_key=key,
        account_id=account_id,
        endpoint=endpoint,
        request_hash=request_hash,
        status=IDEMPOTENCY_IN_PROGRESS,
        created_at=now,
        expires_at=now + IDEMPOTENCY_TTL,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return IdempotencyReservation(record_id=record.id)
    except IntegrityError:
        db.rollback()

    existing = (
        db.query(ApiIdempotencyRequest)
        .filter(
            ApiIdempotencyRequest.idempotency_key == key,
            ApiIdempotencyRequest.account_id == account_id,
            ApiIdempotencyRequest.endpoint == endpoint,
        )
        .first()
    )
    if existing is None:
        raise HTTPException(500, "No se pudo registrar la idempotencia")

    if _is_expired(existing, now):
        return _take_over(db, existing, request_hash, now)

    if existing.status == IDEMPOTENCY_COMPLETED:
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key reutilizada con un payload distinto",
            )
        body = (
            existing.response_body if isinstance(existing.response_body, dict) else {}
        )
        return IdempotencyReservation(
            record_id=existing.id,
            cached=IdempotencyHit(
                status_code=existing.status_code or 200,
                body=body,
            ),
        )

    if existing.status == IDEMPOTENCY_IN_PROGRESS and not _is_stale_in_progress(
        existing, now
    ):
        raise HTTPException(
            status_code=409,
            detail="Este pago ya está en proceso. Espera un momento.",
        )

    return _take_over(db, existing, request_hash, now)


def _take_over(
    db: Session,
    existing: ApiIdempotencyRequest,
    request_hash: str,
    now: datetime,
) -> IdempotencyReservation:
    existing.request_hash = request_hash
    existing.status = IDEMPOTENCY_IN_PROGRESS
    existing.status_code = None
    existing.response_body = None
    existing.created_at = now
    existing.expires_at = now + IDEMPOTENCY_TTL
    db.add(existing)
    db.commit()
    db.refresh(existing)
    logger.info(
        "Idempotency takeover key=%s account=%s endpoint=%s",
        existing.idempotency_key,
        existing.account_id,
        existing.endpoint,
    )
    return IdempotencyReservation(record_id=existing.id)


def complete_idempotency(
    db: Session,
    reservation: IdempotencyReservation,
    status_code: int,
    body: dict,
) -> None:
    record = db.get(ApiIdempotencyRequest, reservation.record_id)
    if record is None:
        return
    record.status = IDEMPOTENCY_COMPLETED
    record.status_code = status_code
    record.response_body = body
    db.add(record)
    db.commit()


def abandon_idempotency(db: Session, reservation: IdempotencyReservation) -> None:
    """Elimina la reserva para que un reintento no quede pegado a un 5xx."""
    try:
        db.rollback()
    except Exception:
        logger.warning("rollback previo a abandonar idempotency falló")
    record = db.get(ApiIdempotencyRequest, reservation.record_id)
    if record is None:
        return
    db.delete(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("No se pudo abandonar reserva idempotency id=%s", record.id)
