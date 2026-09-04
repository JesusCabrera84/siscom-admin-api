"""Tests de endpoints de unidades."""

from uuid import UUID

from fastapi import status

from app.models.unit_device import UnitDevice
from app.models.unit_profile import UnitProfile
from app.models.vehicle_profile import VehicleProfile


def test_create_unit_minimal_creates_default_profile(authenticated_client, db_session):
    payload = {
        "name": "Unidad mínima",
        "description": "Solo campos base",
    }

    response = authenticated_client.post("/api/v1/units/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]

    unit_id = UUID(data["id"])
    profile = (
        db_session.query(UnitProfile).filter(UnitProfile.unit_id == unit_id).first()
    )

    assert profile is not None
    assert profile.unit_type == "vehicle"
    assert profile.icon_type is None
    assert profile.brand is None
    assert profile.model is None
    assert profile.color is None
    assert profile.year is None


def test_create_unit_extended_camel_case_creates_profiles_and_device_assignment(
    authenticated_client, db_session, test_device_data, test_organization_data
):
    test_device_data.organization_id = test_organization_data.id
    test_device_data.status = "entregado"
    db_session.add(test_device_data)
    db_session.commit()

    payload = {
        "name": "Unidad full camel",
        "description": "Con perfil y dispositivo",
        "deviceId": test_device_data.device_id,
        "iconType": "vehicle-car-truck",
        "brand": "Ford",
        "model": "F-350",
        "color": "Rojo",
        "year": 2024,
        "plate": "ABC-123",
        "vin": "1FDUF3GT5GED12345",
    }

    response = authenticated_client.post("/api/v1/units/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    unit_id = UUID(data["id"])

    profile = (
        db_session.query(UnitProfile).filter(UnitProfile.unit_id == unit_id).first()
    )
    assert profile is not None
    assert profile.icon_type == payload["iconType"]
    assert profile.brand == payload["brand"]
    assert profile.model == payload["model"]
    assert profile.color == payload["color"]
    assert profile.year == payload["year"]

    vehicle_profile = (
        db_session.query(VehicleProfile)
        .filter(VehicleProfile.unit_id == unit_id)
        .first()
    )
    assert vehicle_profile is not None
    assert vehicle_profile.plate == payload["plate"]
    assert vehicle_profile.vin == payload["vin"]

    assignment = (
        db_session.query(UnitDevice)
        .filter(UnitDevice.unit_id == unit_id, UnitDevice.unassigned_at.is_(None))
        .first()
    )
    assert assignment is not None
    assert assignment.device_id == payload["deviceId"]

    db_session.refresh(test_device_data)
    assert test_device_data.status == "asignado"
    assert test_device_data.last_assignment_at is not None


def test_create_unit_extended_snake_case_supported(authenticated_client, db_session):
    payload = {
        "name": "Unidad full snake",
        "description": "Con perfiles",
        "icon_type": "vehicle-car-sedan",
        "brand": "Toyota",
        "model": "Hilux",
        "color": "Blanco",
        "year": 2022,
        "plate": "XYZ-987",
        "vin": "1HGCM82633A123456",
    }

    response = authenticated_client.post("/api/v1/units/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    unit_id = UUID(data["id"])

    profile = (
        db_session.query(UnitProfile).filter(UnitProfile.unit_id == unit_id).first()
    )
    assert profile is not None
    assert profile.icon_type == payload["icon_type"]
    assert profile.brand == payload["brand"]
    assert profile.model == payload["model"]
    assert profile.color == payload["color"]
    assert profile.year == payload["year"]

    vehicle_profile = (
        db_session.query(VehicleProfile)
        .filter(VehicleProfile.unit_id == unit_id)
        .first()
    )
    assert vehicle_profile is not None
    assert vehicle_profile.plate == payload["plate"]
    assert vehicle_profile.vin == payload["vin"]


def test_create_unit_with_invalid_device_returns_404(authenticated_client):
    payload = {
        "name": "Unidad con device inválido",
        "deviceId": "000000000000000",
    }

    response = authenticated_client.post("/api/v1/units/", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Dispositivo no encontrado" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Identificadores opacos (Fase 1)
#
# `device_id` es el IMEI y hoy es lo que el cliente web propaga hasta las URLs
# de siscom-api. Estos tests fijan que la API ofrece un identificador opaco
# alternativo en las respuestas de las que el cliente lo toma.
# ---------------------------------------------------------------------------


def _assign_device(db_session, unit_id, device):
    db_session.add(UnitDevice(unit_id=unit_id, device_id=device.device_id))
    db_session.commit()


def test_list_units_exposes_opaque_refs(
    authenticated_client, db_session, test_device_data, test_organization_data
):
    """`GET /units` es la fuente de la que el cliente saca el identificador."""
    test_device_data.organization_id = test_organization_data.id
    test_device_data.status = "entregado"
    db_session.add(test_device_data)
    db_session.commit()

    created = authenticated_client.post(
        "/api/v1/units/",
        json={"name": "Unidad con ref", "deviceId": test_device_data.device_id},
    )
    assert created.status_code == status.HTTP_201_CREATED

    response = authenticated_client.get("/api/v1/units/")
    assert response.status_code == status.HTTP_200_OK

    unit = next(u for u in response.json() if u["name"] == "Unidad con ref")

    assert UUID(unit["unit_ref"])
    assert UUID(unit["device_ref"])
    # El ref es independiente de las claves internas y del IMEI
    assert unit["unit_ref"] != unit["id"]
    assert unit["device_ref"] != unit["device_id"]


def test_unit_detail_exposes_the_assigned_device(
    authenticated_client, db_session, test_device_data, test_organization_data
):
    """
    Antes había que cruzar el detalle con el listado para saber qué dispositivo
    tenía la unidad. El detalle ahora se basta solo.
    """
    test_device_data.organization_id = test_organization_data.id
    test_device_data.status = "entregado"
    db_session.add(test_device_data)
    db_session.commit()

    created = authenticated_client.post(
        "/api/v1/units/",
        json={"name": "Unidad detalle", "deviceId": test_device_data.device_id},
    )
    unit_id = created.json()["id"]

    response = authenticated_client.get(f"/api/v1/units/{unit_id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["device_id"] == test_device_data.device_id
    assert UUID(data["device_ref"]) == test_device_data.device_ref
    assert UUID(data["unit_ref"])


def test_unit_detail_without_device_returns_null_refs(authenticated_client):
    created = authenticated_client.post(
        "/api/v1/units/", json={"name": "Unidad sin dispositivo"}
    )
    unit_id = created.json()["id"]

    data = authenticated_client.get(f"/api/v1/units/{unit_id}").json()
    assert data["device_id"] is None
    assert data["device_ref"] is None
    assert UUID(data["unit_ref"])


def test_sharing_with_the_flag_on_but_no_data_plane_returns_503(
    monkeypatch,
    authenticated_client,
    db_session,
    test_device_data,
    test_organization_data,
):
    """
    El interruptor de la migración puede encenderse antes de que estén las claves
    o Valkey. Ese estado tiene que degradar el endpoint, no reventarlo: un 503
    dice "vuelve luego" y es reversible apagando el flag; un 500 parece un fallo
    del servicio y manda a alguien a depurar donde no toca.
    """
    monkeypatch.setattr(
        "app.api.v1.endpoints.units.settings.SHARE_LOCATION_USE_DATA_TOKEN", True
    )

    test_device_data.organization_id = test_organization_data.id
    test_device_data.status = "entregado"
    db_session.add(test_device_data)
    db_session.commit()

    created = authenticated_client.post(
        "/api/v1/units/",
        json={"name": "Unidad 503", "deviceId": test_device_data.device_id},
    )
    unit_id = created.json()["id"]

    response = authenticated_client.post(f"/api/v1/units/{unit_id}/share-location")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_stop_sharing_without_data_plane_returns_503(authenticated_client):
    """
    Aquí el 503 no es cortesía: la revocación es el único efecto de la llamada, y
    responder 200 sin haber revocado nada le diría a alguien que dejó de
    compartir cuando el enlace sigue vivo.
    """
    created = authenticated_client.post(
        "/api/v1/units/", json={"name": "Unidad stop-share"}
    )
    unit_id = created.json()["id"]

    response = authenticated_client.delete(f"/api/v1/units/{unit_id}/share-location")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
