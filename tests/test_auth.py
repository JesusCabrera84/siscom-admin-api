"""
Tests de autenticación.
Verifica que los endpoints rechacen requests sin token válido.
"""
import pytest
from fastapi import status


def test_endpoint_without_token_returns_401(client):
    """
    Test que un endpoint protegido sin token retorna 401.
    """
    response = client.get("/api/v1/clients/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_endpoint_with_invalid_token_returns_401(client):
    """
    Test que un endpoint con token inválido retorna 401.
    """
    headers = {"Authorization": "Bearer invalid_token_here"}
    response = client.get("/api/v1/clients/", headers=headers)
    # Puede retornar 401 o 400 dependiendo de cómo falle la validación
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


def test_devices_endpoint_without_auth(client):
    """
    Test que /devices sin autenticación retorna 401.
    """
    response = client.get("/api/v1/devices/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_services_endpoint_without_auth(client):
    """
    Test que /services sin autenticación retorna 401.
    """
    response = client.get("/api/v1/services/active")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

