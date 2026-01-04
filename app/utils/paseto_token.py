"""
Utilidades para generación de tokens PASETO.

Soporta dos tipos de tokens:
1. Tokens de compartir ubicación (scope: public-location-share)
2. Tokens de servicio para aplicaciones externas (scope: internal-gac-admin)
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

import pyseto
from pyseto import Key

from app.core.config import settings

# Roles válidos para tokens de servicio
ServiceRole = Literal["GAC_ADMIN"]

# Servicios válidos
ServiceName = Literal["gac"]


class PasetoTokenGenerator:
    """
    Generador de tokens PASETO v4.local para compartir ubicación de unidades.
    """

    def __init__(self):
        """
        Inicializa el generador con la clave secreta de la configuración.
        La clave debe ser de 32 bytes para PASETO v4.local.
        """
        # Decodificar la clave desde base64 (debe ser de 32 bytes)
        secret = base64.b64decode(settings.PASETO_SECRET_KEY)
        if len(secret) < 32:
            # Pad con ceros si es menor
            secret = secret.ljust(32, b"\0")
        elif len(secret) > 32:
            # Truncar si es mayor
            secret = secret[:32]

        self.key = Key.new(version=4, purpose="local", key=secret)

    def generate_share_token(
        self, unit_id: UUID, device_id: str, expires_in_minutes: int = 30
    ) -> tuple[str, datetime]:
        """
        Genera un token PASETO para compartir la ubicación de una unidad.

        Args:
            unit_id: ID de la unidad a compartir
            device_id: ID del dispositivo asignado a la unidad
            expires_in_minutes: Tiempo de expiración en minutos (default: 30)

        Returns:
            tuple: (token, fecha_expiracion)

        Raises:
            ValueError: Si device_id esta vacio o es None
        """
        if not device_id:
            raise ValueError("La unidad no tiene asignado un dispositivo")

        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=expires_in_minutes)

        payload = {
            "share_id": str(uuid4()),
            "unit_id": str(unit_id),
            "device_id": device_id,
            "scope": "public-location-share",
            "iat": now.isoformat(),
            "exp": exp.isoformat(),
        }

        # Codificar el payload como JSON bytes
        payload_bytes = json.dumps(payload).encode("utf-8")

        # La version y proppsito ya estan definidos en self.key (v4.local)
        token = pyseto.encode(
            key=self.key,
            payload=payload_bytes,
        )

        return token.decode("utf-8"), exp

    def decode_share_token(self, token: str) -> dict | None:
        """
        Decodifica y valida un token PASETO de compartir ubicacion.

        Args:
            token: Token PASETO a decodificar

        Returns:
            dict: Payload del token si es valido, None si es inválido o expirado
        """
        try:
            decoded = pyseto.decode(keys=self.key, token=token)
            payload = json.loads(decoded.payload.decode("utf-8"))

            # Validar expiracion
            exp = datetime.fromisoformat(payload["exp"])
            if datetime.now(timezone.utc) > exp:
                return None

            # Validar scope
            if payload.get("scope") not in ["public-location-share"]:
                return None

            return payload
        except Exception:
            return None

    def generate_service_token(
        self,
        service: str,
        role: str,
        expires_in_hours: int = 24,
        additional_claims: Optional[dict] = None,
    ) -> tuple[str, datetime]:
        """
        Genera un token PASETO para autenticación de servicios externos.

        Args:
            service: Nombre del servicio (ej: "gac")
            role: Rol del servicio (ej: "GAC_ADMIN")
            expires_in_hours: Tiempo de expiración en horas (default: 24)
            additional_claims: Claims adicionales opcionales

        Returns:
            tuple: (token, fecha_expiracion)
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=expires_in_hours)

        payload = {
            "token_id": str(uuid4()),
            "service": service,
            "role": role,
            "scope": "internal-gac-admin",
            "iat": now.isoformat(),
            "exp": exp.isoformat(),
        }

        # Agregar claims adicionales si se proporcionan
        if additional_claims:
            payload.update(additional_claims)

        # Codificar el payload como JSON bytes
        payload_bytes = json.dumps(payload).encode("utf-8")

        token = pyseto.encode(
            key=self.key,
            payload=payload_bytes,
        )

        return token.decode("utf-8"), exp

    def decode_service_token(
        self,
        token: str,
        required_service: Optional[str] = None,
        required_role: Optional[str] = None,
    ) -> dict | None:
        """
        Decodifica y valida un token PASETO de servicio.

        Args:
            token: Token PASETO a decodificar
            required_service: Si se proporciona, valida que el service coincida
            required_role: Si se proporciona, valida que el role coincida

        Returns:
            dict: Payload del token si es válido, None si es inválido o expirado
        """
        try:
            decoded = pyseto.decode(keys=self.key, token=token)
            payload = json.loads(decoded.payload.decode("utf-8"))

            # Validar expiración
            exp = datetime.fromisoformat(payload["exp"])
            if datetime.now(timezone.utc) > exp:
                return None

            # Validar scope - aceptar scopes de servicio válidos
            # Permite tokens de diferentes sistemas (gac-api, nexus-admin, etc.)
            valid_service_scopes = {
                "service-auth",
                "internal-nexus-admin",
                "internal-gac-admin",
                "internal-app-admin",
            }
            scope = payload.get("scope")
            if scope and scope not in valid_service_scopes:
                # Ser más flexible: si tiene service="gac", aceptar cualquier scope que empiece con "internal"
                if payload.get("service") == "gac" and scope.startswith("internal"):
                    pass  # Aceptar
                else:
                    return None

            # Validar service si se requiere
            if required_service and payload.get("service") != required_service:
                return None

            # Validar role si se requiere
            if required_role and payload.get("role") != required_role:
                return None

            return payload
        except Exception:
            return None

    def decode_any_token(self, token: str) -> dict | None:
        """
        Intenta decodificar cualquier token PASETO válido (share o service).

        Args:
            token: Token PASETO a decodificar

        Returns:
            dict: Payload del token si es válido, None si es inválido o expirado
        """
        try:
            decoded = pyseto.decode(keys=self.key, token=token)
            payload = json.loads(decoded.payload.decode("utf-8"))

            # Validar expiración
            exp = datetime.fromisoformat(payload["exp"])
            if datetime.now(timezone.utc) > exp:
                return None

            return payload
        except Exception:
            return None


# Instancia singleton para uso en la aplicacion
paseto_generator = PasetoTokenGenerator()


def generate_location_share_token(
    unit_id: UUID, device_id: str, expires_in_minutes: int = 30
) -> tuple[str, datetime]:
    """
    Función helper para generar un token de compartir ubicación.

    Args:
        unit_id: ID de la unidad a compartir
        device_id: ID del dispositivo asignado a la unidad
        expires_in_minutes: Tiempo de expiración en minutos (default: 30)

    Returns:
        tuple: (token, fecha_expiracion)

    Raises:
        ValueError: Si device_id estรก vacรญo o es None
    """
    return paseto_generator.generate_share_token(unit_id, device_id, expires_in_minutes)


def decode_location_share_token(token: str) -> dict | None:
    """
    Función helper para decodificar un token de compartir ubicación.

    Args:
        token: Token PASETO a decodificar

    Returns:
        dict: Payload del token si es válido, None si es inválido o expirado
    """
    return paseto_generator.decode_share_token(token)


def generate_service_token(
    service: str,
    role: str,
    expires_in_hours: int = 24,
    additional_claims: Optional[dict] = None,
) -> tuple[str, datetime]:
    """
    Función helper para generar un token de servicio.

    Args:
        service: Nombre del servicio (ej: "gac")
        role: Rol del servicio (ej: "GAC_ADMIN")
        expires_in_hours: Tiempo de expiración en horas (default: 24)
        additional_claims: Claims adicionales opcionales

    Returns:
        tuple: (token, fecha_expiracion)
    """
    return paseto_generator.generate_service_token(
        service, role, expires_in_hours, additional_claims
    )


def decode_service_token(
    token: str,
    required_service: Optional[str] = None,
    required_role: Optional[str] = None,
) -> dict | None:
    """
    Función helper para decodificar un token de servicio.

    Args:
        token: Token PASETO a decodificar
        required_service: Si se proporciona, valida que el service coincida
        required_role: Si se proporciona, valida que el role coincida

    Returns:
        dict: Payload del token si es válido, None si es inválido o expirado
    """
    return paseto_generator.decode_service_token(token, required_service, required_role)
