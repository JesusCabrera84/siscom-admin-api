"""Cliente REST de Facturapi sin red."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.facturapi_client import (
    FacturapiClient,
    FacturapiError,
    facturapi_livemode,
)


def _json_response(status_code: int, payload):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = b"{}" if not isinstance(payload, (bytes, bytearray)) else payload
    resp.json.return_value = payload
    resp.text = "error"
    return resp


def _request_mock(response):
    client_cm = MagicMock()
    client_cm.__enter__.return_value.request.return_value = response
    return client_cm


def test_livemode_from_key_prefix():
    assert facturapi_livemode("sk_live_abc") is True
    assert facturapi_livemode("sk_test_abc") is False
    assert facturapi_livemode(None) is False


def test_missing_api_key_is_503():
    client = FacturapiClient(api_key="")
    with pytest.raises(FacturapiError) as ei:
        client.create_customer({"legal_name": "Acme"})
    assert ei.value.status_code == 503
    assert "no está configurada" in ei.value.detail


@patch("app.services.facturapi_client.httpx.Client")
def test_create_customer_posts_json(mock_cls):
    mock_cls.return_value = _request_mock(_json_response(200, {"id": "cus_1"}))
    client = FacturapiClient(api_key="sk_test_x")
    out = client.create_customer({"legal_name": "Acme", "tax_id": "ABC101010111"})
    assert out["id"] == "cus_1"
    args, kwargs = mock_cls.return_value.__enter__.return_value.request.call_args
    assert args[0] == "POST"
    assert args[1].endswith("/customers")
    assert kwargs["headers"]["Authorization"] == "Bearer sk_test_x"


@patch("app.services.facturapi_client.httpx.Client")
def test_facturapi_400_returns_human_message(mock_cls):
    mock_cls.return_value = _request_mock(
        _json_response(400, {"message": "RFC inválido para el régimen 601"})
    )
    client = FacturapiClient(api_key="sk_test_x")
    with pytest.raises(HTTPException) as ei:
        client.create_customer({"tax_id": "XXX"})
    assert ei.value.status_code == 400
    assert ei.value.detail == "RFC inválido para el régimen 601"
    assert "[object Object]" not in str(ei.value.detail)


@patch("app.services.facturapi_client.httpx.Client")
def test_update_customer_404_creates_new(mock_cls):
    request = MagicMock()
    request.side_effect = [
        _json_response(404, {"message": "Customer not found"}),
        _json_response(200, {"id": "cus_new"}),
    ]
    client_cm = MagicMock()
    client_cm.__enter__.return_value.request = request
    mock_cls.return_value = client_cm

    client = FacturapiClient(api_key="sk_test_x")
    out = client.create_or_update_customer({"legal_name": "Acme"}, "cus_old")
    assert out["id"] == "cus_new"
    assert request.call_count == 2
    assert request.call_args_list[0].args[0] == "PUT"
    assert request.call_args_list[1].args[0] == "POST"


@patch("app.services.facturapi_client.httpx.Client")
def test_get_invoice_file_returns_bytes(mock_cls):
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"%PDF-cfdi"
    resp.json.side_effect = AssertionError("no json")
    mock_cls.return_value = _request_mock(resp)
    client = FacturapiClient(api_key="sk_test_x")
    content = client.get_invoice_file("inv_1", "pdf")
    assert content == b"%PDF-cfdi"
    args, kwargs = mock_cls.return_value.__enter__.return_value.request.call_args
    assert args[1].endswith("/invoices/inv_1/pdf")
    assert "Content-Type" not in kwargs["headers"]
