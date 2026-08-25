"""Cliente REST de Facturapi. La secret key nunca sale de este módulo."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings

FACTURAPI_BASE = "https://www.facturapi.io/v2"


class FacturapiError(HTTPException):
    """Error de Facturapi ya convertido a texto para el cliente."""


def facturapi_livemode(api_key: str | None = None) -> bool:
    key = api_key if api_key is not None else settings.FACTURAPI_API_KEY
    return bool(key) and str(key).startswith("sk_live_")


def _human_error(body: Any, status_code: int) -> str:
    if isinstance(body, dict):
        msg = body.get("message") or body.get("error")
        if isinstance(msg, dict):
            msg = msg.get("message") or msg.get("msg") or msg.get("details")
        if isinstance(msg, list) and msg:
            first = msg[0]
            if isinstance(first, dict):
                msg = first.get("message") or first.get("msg") or first.get("details")
            elif isinstance(first, str):
                msg = first
        if isinstance(msg, str) and msg.strip() and msg.strip() != "[object Object]":
            return msg.strip()
    return f"Facturapi respondió {status_code}"


class FacturapiClient:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self.api_key = api_key if api_key is not None else settings.FACTURAPI_API_KEY
        self.timeout = timeout

    def require_configured(self) -> None:
        if not self.api_key:
            raise FacturapiError(
                503, "La facturación fiscal no está configurada en el servidor."
            )

    @property
    def livemode(self) -> bool:
        return facturapi_livemode(self.api_key)

    def _headers(self, *, json_body: bool) -> dict[str, str]:
        self.require_configured()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        binary: bool = False,
    ) -> Any:
        url = f"{FACTURAPI_BASE}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(
                    method,
                    url,
                    headers=self._headers(json_body=json is not None),
                    json=json,
                )
        except httpx.TimeoutException as exc:
            raise FacturapiError(
                504, "Facturapi no respondió a tiempo. Intenta de nuevo."
            ) from exc
        except httpx.HTTPError as exc:
            raise FacturapiError(
                502, "No se pudo conectar con el servicio de facturación fiscal."
            ) from exc

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = {"message": (resp.text or "")[:300]}
            status = (
                404
                if resp.status_code == 404
                else (400 if resp.status_code < 500 else 502)
            )
            raise FacturapiError(status, _human_error(body, resp.status_code))

        if binary:
            return resp.content
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def create_customer(self, payload: dict) -> dict:
        return self._request("POST", "/customers", json=payload)

    def update_customer(self, customer_id: str, payload: dict) -> dict:
        return self._request("PUT", f"/customers/{customer_id}", json=payload)

    def create_or_update_customer(
        self, payload: dict, existing_id: str | None = None
    ) -> dict:
        if existing_id:
            try:
                return self.update_customer(existing_id, payload)
            except FacturapiError as exc:
                if exc.status_code != 404:
                    raise
        created = self.create_customer(payload)
        if not isinstance(created, dict) or not created.get("id"):
            raise FacturapiError(502, "Facturapi no devolvió el cliente fiscal.")
        return created

    def create_invoice(self, payload: dict) -> dict:
        return self._request("POST", "/invoices", json=payload)

    def get_invoice_file(self, invoice_id: str, fmt: str) -> bytes:
        if fmt not in {"pdf", "xml"}:
            raise FacturapiError(400, "Formato de CFDI no soportado.")
        content = self._request("GET", f"/invoices/{invoice_id}/{fmt}", binary=True)
        if not isinstance(content, (bytes, bytearray)):
            raise FacturapiError(502, "Facturapi no devolvió el archivo del CFDI.")
        return bytes(content)
