"""
Utilidades para generación de tokens PASETO.

Soporta dos tipos de tokens, **cada uno con su propia clave**:

1. Tokens de compartir ubicación (scope: public-location-share)
   → firmados con `SHARE_LOCATION_KEY_B64`.
2. Tokens de servicio para aplicaciones externas (scope: internal-gac-admin)
   → firmados con `PASETO_SECRET_KEY`.

POR QUÉ DOS CLAVES
==================
PASETO v4.local es simétrico: quien verifica también puede firmar. Los tokens
de compartir ubicación se verifican en siscom-api, así que ese servicio necesita
la clave con la que se firman. Mientras ambos tipos compartieron clave,
siscom-api podía emitir tokens `internal-gac-admin` y llamar a la API interna de
este servicio como administrador (ver `app/api/deps.py`,
`get_auth_cognito_or_paseto`). Separar las claves corta esa vía: siscom-api solo
recibe `SHARE_LOCATION_KEY_B64`, con la que no puede firmar nada administrativo.

Esta separación es el paso previo a migrar los tokens de compartir a v4.public
(Ed25519), donde el verificador ya no podrá firmar en absoluto.
"""

import base64
import binascii
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

import pyseto
from pyseto import Key

from app.core.config import settings

logger = logging.getLogger(__name__)

# Longitud exacta que exige PASETO v4.local.
_V4_LOCAL_KEY_BYTES = 32


class ShareLocationKeyNotConfigured(RuntimeError):
    """
    `SHARE_LOCATION_KEY_B64` no está configurada.

    Se falla en el punto de uso (y no al arrancar) para que la ausencia del
    secreto deje sin servicio únicamente el endpoint de compartir ubicación en
    vez de tumbar la API entera. Nunca se degrada a `PASETO_SECRET_KEY`: eso
    reintroduciría la escalada de privilegios que esta separación elimina.
    """


def _decode_key_material(secret_b64: str, label: str) -> bytes:
    """Decodifica base64 y valida que el material tenga exactamente 32 bytes."""
    try:
        raw = base64.b64decode(secret_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{label} no es base64 válido") from exc

    if len(raw) != _V4_LOCAL_KEY_BYTES:
        raise ValueError(
            f"{label} debe decodificar a exactamente {_V4_LOCAL_KEY_BYTES} bytes; "
            f"tiene {len(raw)}"
        )

    if not any(raw):
        raise ValueError(
            f"{label} es todo ceros: es el valor de ejemplo de .env.example, "
            "no una clave real"
        )

    return raw


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
        Inicializa el generador con las dos claves de la configuración.

        - `service_key` (PASETO_SECRET_KEY): tokens `internal-*`. Se conserva el
          relleno/truncado histórico para no romper entornos ya desplegados con
          una clave de longitud distinta de 32 bytes, pero se avisa por log.
        - `share_key` (SHARE_LOCATION_KEY_B64): tokens de compartir ubicación.
          Validación estricta; si falta, se resuelve perezosamente y el endpoint
          de compartir devuelve 503.
        """
        self.service_key = Key.new(
            version=4, purpose="local", key=self._load_service_key_material()
        )

        # Se resuelve de forma perezosa: la ausencia del secreto no debe impedir
        # el arranque de la API, solo deshabilitar compartir ubicación.
        self._share_key: Optional[Key] = None
        if settings.SHARE_LOCATION_KEY_B64:
            # Validación temprana: una clave presente pero inválida es un error
            # de configuración que conviene ver al arrancar, no en la primera
            # petición de un usuario.
            self._share_key = Key.new(
                version=4,
                purpose="local",
                key=_decode_key_material(
                    settings.SHARE_LOCATION_KEY_B64, "SHARE_LOCATION_KEY_B64"
                ),
            )
        else:
            logger.warning(
                "SHARE_LOCATION_KEY_B64 no está configurada: compartir ubicación "
                "responderá 503. No se usa PASETO_SECRET_KEY como sustituta "
                "porque daría a siscom-api la clave de los tokens internos."
            )

    @staticmethod
    def _load_service_key_material() -> bytes:
        """
        Material de clave para los tokens de servicio.

        Mantiene el relleno/truncado histórico —cambiarlo invalidaría los tokens
        de servicio ya emitidos y podría impedir el arranque en producción— pero
        registra el problema para que se pueda corregir con una rotación
        planificada.

        El relleno es peor que su ausencia, y conviene tenerlo presente al
        retirarlo: convierte una clave inválida en una de longitud válida, con lo
        que **este** lado parece correcto —32 bytes, ninguna comprobación salta—
        mientras el verificador, que no rellena, deriva otra clave distinta. Al
        retirarlo hay que hacerlo fallando al arrancar, no dejando de rellenar en
        silencio, o el fallo simplemente cambia de forma.
        """
        secret = base64.b64decode(settings.PASETO_SECRET_KEY)

        if len(secret) != _V4_LOCAL_KEY_BYTES:
            logger.warning(
                "PASETO_SECRET_KEY decodifica a %d bytes en lugar de %d. Se "
                "rellena/trunca por compatibilidad, con dos consecuencias: la "
                "entropía efectiva es la de %d bytes, y —más grave— los servicios "
                "que verifican sin rellenar derivan una clave DISTINTA, así que "
                "los tokens firmados aquí no validan allí aunque tengan la misma "
                "cadena configurada. Rotar a base64 estricto de %d bytes.",
                len(secret),
                _V4_LOCAL_KEY_BYTES,
                len(secret),
                _V4_LOCAL_KEY_BYTES,
            )
            if len(secret) < _V4_LOCAL_KEY_BYTES:
                secret = secret.ljust(_V4_LOCAL_KEY_BYTES, b"\0")
            else:
                secret = secret[:_V4_LOCAL_KEY_BYTES]

        if not any(secret):
            logger.error(
                "PASETO_SECRET_KEY es todo ceros: es el valor de .env.example. "
                "Cualquiera puede firmar tokens de servicio internos. Rotar ya."
            )

        return secret

    @property
    def share_key(self) -> Key:
        """Clave de compartir ubicación, o error si no está configurada."""
        if self._share_key is None:
            raise ShareLocationKeyNotConfigured(
                "SHARE_LOCATION_KEY_B64 no está configurada"
            )
        return self._share_key

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
            ShareLocationKeyNotConfigured: Si falta SHARE_LOCATION_KEY_B64
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

        # Clave dedicada: estos tokens los verifica siscom-api.
        token = pyseto.encode(
            key=self.share_key,
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
            decoded = pyseto.decode(keys=self.share_key, token=token)
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
            key=self.service_key,
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
            decoded = pyseto.decode(keys=self.service_key, token=token)
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
