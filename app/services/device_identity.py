"""
Resolución de identificadores de dispositivo.

`devices.device_id` es el IMEI (la migración 005 renombró la columna `imei`, no
creó un identificador nuevo), así que direccionar un dispositivo por `device_id`
en una URL deja el IMEI en los logs de acceso de uvicorn y del ALB, y en las
cabeceras Referer. `devices.device_ref` es un identificador opaco pensado para
ocupar ese lugar.

Durante la migración conviven ambos: los clientes que ya envían `device_ref` no
filtran el IMEI, y los que aún no han migrado siguen funcionando. Estas funciones
aceptan cualquiera de los dos y devuelven siempre el `device_id` interno.

No hay ambigüedad posible entre ambos espacios: un `device_ref` es un UUID y un
IMEI nunca lo es.
"""

from __future__ import annotations

from typing import Dict, List, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.device import Device


def _as_uuid(value: str) -> UUID | None:
    """Devuelve el UUID si `value` lo es, o None si es un device_id (IMEI)."""
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def resolve_device_identifiers(db: Session, values: Sequence[str]) -> List[str]:
    """
    Traduce una lista de identificadores mixtos a `device_id` internos.

    Los valores con forma de UUID se resuelven contra `devices.device_ref`; el
    resto se devuelven tal cual. Se preserva el orden de entrada.

    Un `device_ref` que no existe se deja pasar sin traducir: la autorización es
    responsabilidad de quien llama (`validate_device_access`), y resolverlo aquí
    a un error distinto revelaría qué refs existen y cuáles no.
    """
    refs = {v: u for v in values if (u := _as_uuid(v)) is not None}
    if not refs:
        return list(values)

    rows = (
        db.query(Device.device_ref, Device.device_id)
        .filter(Device.device_ref.in_(refs.values()))
        .all()
    )
    by_ref: Dict[UUID, str] = {row.device_ref: row.device_id for row in rows}

    return [by_ref.get(refs[v], v) if v in refs else v for v in values]


def resolve_device_identifier(db: Session, value: str) -> str:
    """Versión de un solo valor de `resolve_device_identifiers`."""
    return resolve_device_identifiers(db, [value])[0]
