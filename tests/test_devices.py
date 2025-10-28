"""
Tests de endpoints de dispositivos.
"""
import pytest
from fastapi import status


def test_list_devices(authenticated_client, test_device_data):
    """
    Test que lista dispositivos del cliente autenticado.
    """
    response = authenticated_client.get("/api/v1/devices/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["imei"] == test_device_data.imei


def test_create_device(authenticated_client, test_client_data):
    """
    Test que crea un nuevo dispositivo.
    """
    device_data = {
        "imei": "999888777666555",
        "brand": "TestBrand",
        "model": "TestModel",
    }
    response = authenticated_client.post("/api/v1/devices/", json=device_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["imei"] == device_data["imei"]
    assert data["brand"] == device_data["brand"]
    assert data["active"] is False


def test_create_device_duplicate_imei(authenticated_client, test_device_data):
    """
    Test que no permite crear dispositivo con IMEI duplicado.
    """
    device_data = {
        "imei": test_device_data.imei,  # IMEI ya existe
        "brand": "TestBrand",
        "model": "TestModel",
    }
    response = authenticated_client.post("/api/v1/devices/", json=device_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_get_device_detail(authenticated_client, test_device_data):
    """
    Test que obtiene el detalle de un dispositivo.
    """
    response = authenticated_client.get(f"/api/v1/devices/{test_device_data.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_device_data.id)
    assert data["imei"] == test_device_data.imei


def test_list_unassigned_devices(authenticated_client, test_device_data):
    """
    Test que lista dispositivos no asignados a unidades.
    """
    response = authenticated_client.get("/api/v1/devices/unassigned")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    # El dispositivo de prueba no está asignado
    assert any(d["id"] == str(test_device_data.id) for d in data)

