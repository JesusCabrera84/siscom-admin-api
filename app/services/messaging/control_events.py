"""Contratos de control-plane publicados por siscom-admin-api."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from app.utils.datetime import utcnow

logger = logging.getLogger(__name__)


def to_utc_iso_z(value: datetime | None) -> str:
    dt = value or utcnow()
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat() + "Z"


def _as_str(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def build_control_event(
    event_type: str,
    entity: str,
    organization_id: UUID | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "entity": entity,
        "timestamp": to_utc_iso_z(utcnow()),
        "organization_id": _as_str(organization_id),
        "data": data,
    }


def build_unit_device_event(
    *,
    event_type: str,
    device_id: str,
    organization_id: UUID | None,
    unit_id: UUID | None,
    previous_unit_id: UUID | None = None,
    previous_organization_id: UUID | None = None,
    is_active: bool,
) -> dict[str, Any]:
    return build_control_event(
        event_type=event_type,
        entity="unit_device",
        organization_id=organization_id,
        data={
            "device_id": device_id,
            "unit_id": _as_str(unit_id),
            "previous_unit_id": _as_str(previous_unit_id),
            "previous_organization_id": _as_str(previous_organization_id),
            "is_active": is_active,
        },
    )


def build_user_unit_event(
    *,
    event_type: str,
    organization_id: UUID,
    user_id: UUID,
    unit_id: UUID,
    role: str | None = None,
) -> dict[str, Any]:
    return build_control_event(
        event_type=event_type,
        entity="user_unit",
        organization_id=organization_id,
        data={
            "user_id": str(user_id),
            "unit_id": str(unit_id),
            "role": role,
        },
    )


def build_user_device_event(
    *,
    event_type: str,
    organization_id: UUID | None,
    device_row_id: UUID,
    user_id: UUID,
    device_token: str,
    platform: str,
    endpoint_arn: str | None,
    is_active: bool,
    updated_at: datetime | None,
) -> dict[str, Any]:
    return build_control_event(
        event_type=event_type,
        entity="user_device",
        organization_id=organization_id,
        data={
            "id": str(device_row_id),
            "user_id": str(user_id),
            "device_token": device_token,
            "platform": platform,
            "endpoint_arn": endpoint_arn,
            "is_active": is_active,
            "updated_at": to_utc_iso_z(updated_at),
        },
    )


def publish_control_event(
    producer: Any,
    payload: dict[str, Any],
    key: Optional[str],
    endpoint: str,
) -> None:
    try:
        published = producer.publish_update(payload=payload, key=key)
    except Exception:
        logger.exception(
            "Excepcion inesperada publicando evento de control en Kafka.",
            extra={
                "extra_data": {
                    "endpoint": endpoint,
                    "entity": payload.get("entity"),
                    "event_type": payload.get("event_type"),
                    "key": key,
                }
            },
        )
        return

    if not published:
        logger.error(
            "Fallo publicando evento de control en Kafka.",
            extra={
                "extra_data": {
                    "endpoint": endpoint,
                    "entity": payload.get("entity"),
                    "event_type": payload.get("event_type"),
                    "key": key,
                }
            },
        )
