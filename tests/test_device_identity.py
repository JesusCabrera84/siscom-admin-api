"""
Tests de la resolución de identificadores de dispositivo.

`device_id` es el IMEI; `device_ref` es el identificador opaco que lo sustituye
en las URLs. Estas pruebas fijan que ambos espacios conviven sin ambigüedad
durante la migración.
"""

from uuid import UUID, uuid4

import pytest

from app.models.device import Device
from app.services.device_identity import (
    resolve_device_identifier,
    resolve_device_identifiers,
)


@pytest.fixture
def two_devices(db_session):
    devices = [
        Device(device_id="111111111111111", brand="Queclink", status="nuevo"),
        Device(device_id="222222222222222", brand="Suntech", status="nuevo"),
    ]
    for d in devices:
        db_session.add(d)
    db_session.commit()
    for d in devices:
        db_session.refresh(d)
    return devices


def test_devices_get_an_opaque_ref_automatically(two_devices):
    for device in two_devices:
        assert isinstance(device.device_ref, UUID)


def test_refs_are_distinct_between_devices(two_devices):
    a, b = two_devices
    assert a.device_ref != b.device_ref


def test_ref_is_not_derived_from_the_imei(two_devices):
    """El ref debe ser opaco: nada del IMEI puede reconstruirse a partir de él."""
    device = two_devices[0]
    assert device.device_id not in str(device.device_ref)


def test_resolves_a_ref_to_its_device_id(db_session, two_devices):
    device = two_devices[0]
    assert (
        resolve_device_identifier(db_session, str(device.device_ref))
        == device.device_id
    )


def test_passes_through_a_plain_device_id(db_session, two_devices):
    """Los clientes que aún envían IMEI siguen funcionando."""
    assert resolve_device_identifier(db_session, "111111111111111") == "111111111111111"


def test_preserves_order_with_mixed_identifiers(db_session, two_devices):
    a, b = two_devices
    resolved = resolve_device_identifiers(
        db_session, [str(b.device_ref), a.device_id, str(a.device_ref)]
    )
    assert resolved == [b.device_id, a.device_id, a.device_id]


def test_unknown_ref_is_passed_through_untouched(db_session, two_devices):
    """
    Un ref inexistente no se distingue aquí de uno sin permiso: la autorización
    la hace `validate_device_access`, que responde 404 en ambos casos. Resolverlo
    a un error distinto revelaría qué refs existen.
    """
    missing = str(uuid4())
    assert resolve_device_identifiers(db_session, [missing]) == [missing]


def test_empty_input_needs_no_query(db_session):
    assert resolve_device_identifiers(db_session, []) == []


def test_non_uuid_garbage_is_not_treated_as_a_ref(db_session, two_devices):
    for value in ["", "not-a-uuid", "864537040123456", "0"]:
        assert resolve_device_identifiers(db_session, [value]) == [value]
