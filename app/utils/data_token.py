"""
Emisión del data token del plano de datos (Fase 1).

QUÉ ES
======
Una credencial de vida corta que autoriza a leer datos de unos dispositivos en
siscom-api, y **nada más**. Su carga útil es exhaustivamente:

    {jti, scope_ref, aud, iat, nbf, exp}

Sin `user_id`, sin `organization_id`, sin email, sin lista de dispositivos. No es
una convención que haya que respetar: es que no hay dónde meter la identidad. Un
observador del token —o siscom-api entera— no puede aprender nada de ningún
cliente, porque el token es un puntero opaco y una ventana temporal.

`scope_ref` se resuelve contra Valkey, donde vive el conjunto de identificadores
que ese alcance permite. Borrar esa clave es la revocación.

POR QUÉ v4.public Y NO v4.local
===============================
v4.local es simétrico: quien verifica puede firmar. Como el verificador es otro
servicio, eso le daría capacidad de emitir credenciales. Con Ed25519, siscom-api
tiene la clave pública y no puede firmar nada. Ver ADR-004 para el incidente que
motivó la distinción.

El `kid` viaja en el footer del PASETO —que va en claro y autenticado— para poder
rotar la clave con una ventana de solapamiento en vez de con un corte.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import pyseto
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pyseto import Key

from app.core.config import settings

logger = logging.getLogger(__name__)


class DataTokenKeyNotConfigured(RuntimeError):
    """
    Falta `DATA_TOKEN_PRIVATE_KEY_B64`.

    Se falla en el punto de uso y no al arrancar, para que la ausencia del
    secreto deje sin servicio la emisión del data token en lugar de tumbar la
    API entera. No hay degradación a ninguna otra clave.
    """


@dataclass(frozen=True)
class IssuedDataToken:
    """Resultado de una emisión."""

    token: str
    jti: UUID
    scope_ref: UUID
    issued_at: datetime
    expires_at: datetime


def compute_expiry(
    now: datetime,
    *,
    next_scope_boundary: Optional[datetime] = None,
    max_ttl_seconds: Optional[int] = None,
    min_ttl_seconds: Optional[int] = None,
) -> datetime:
    """
    Vigencia del token: `min(ahora + TTL máximo, siguiente límite del alcance)`.

    El TTL no es una constante global sino una propiedad del dato. Las reglas de
    visibilidad de team (`team.visibility_rules.schedule`) tienen ventanas
    horarias, así que la respuesta del resolver deja de ser cierta a una hora
    conocida. Emitir hasta ese instante hace que el cierre —y también la
    apertura— de una ventana sea exacto, sin pagar TTLs cortos para todo el mundo.

    Se aplica un suelo: si el límite está a cuatro segundos, un token de cuatro
    segundos no le sirve a nadie; mejor uno corto y que el cliente refresque.
    """
    max_ttl = (
        settings.DATA_TOKEN_MAX_TTL_SECONDS
        if max_ttl_seconds is None
        else max_ttl_seconds
    )
    min_ttl = (
        settings.DATA_TOKEN_MIN_TTL_SECONDS
        if min_ttl_seconds is None
        else min_ttl_seconds
    )

    expiry = now + timedelta(seconds=max_ttl)

    if next_scope_boundary is not None and next_scope_boundary < expiry:
        expiry = next_scope_boundary

    floor = now + timedelta(seconds=min_ttl)
    return max(expiry, floor)


def _decode_private_key(secret_b64: str) -> bytes:
    """Decodifica el PEM desde base64 y comprueba que es una Ed25519 privada."""
    try:
        pem = base64.b64decode(secret_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("DATA_TOKEN_PRIVATE_KEY_B64 no es base64 válido") from exc

    try:
        loaded = serialization.load_pem_private_key(pem, password=None)
    except Exception as exc:
        raise ValueError(
            "DATA_TOKEN_PRIVATE_KEY_B64 no contiene un PEM de clave privada"
        ) from exc

    if not isinstance(loaded, Ed25519PrivateKey):
        raise ValueError(
            "DATA_TOKEN_PRIVATE_KEY_B64 debe ser Ed25519; PASETO v4.public no "
            f"admite {type(loaded).__name__}"
        )

    return pem


class DataTokenIssuer:
    """
    Firma data tokens. Este servicio **solo emite**: no hay función de
    verificación porque quien verifica es siscom-api, con la clave pública.
    """

    def __init__(self) -> None:
        self._key: Optional[Key] = None
        self._private_pem: Optional[bytes] = None

        if settings.DATA_TOKEN_PRIVATE_KEY_B64:
            # Una clave presente pero inválida es un error de configuración que
            # conviene ver al arrancar, no en la primera petición de un usuario.
            self._private_pem = _decode_private_key(settings.DATA_TOKEN_PRIVATE_KEY_B64)
            self._key = Key.new(version=4, purpose="public", key=self._private_pem)
        else:
            logger.warning(
                "DATA_TOKEN_PRIVATE_KEY_B64 no está configurada: la emisión de "
                "data tokens responderá 503."
            )

    @property
    def key(self) -> Key:
        if self._key is None:
            raise DataTokenKeyNotConfigured(
                "DATA_TOKEN_PRIVATE_KEY_B64 no está configurada"
            )
        return self._key

    @property
    def is_configured(self) -> bool:
        return self._key is not None

    def public_key_pem(self) -> str:
        """
        Clave pública en PEM, la que hay que entregar a siscom-api.

        Se deriva de la privada en vez de configurarse aparte: así es imposible
        publicar una pública que no case con la que firma.
        """
        if self._private_pem is None:
            raise DataTokenKeyNotConfigured(
                "DATA_TOKEN_PRIVATE_KEY_B64 no está configurada"
            )
        private = serialization.load_pem_private_key(self._private_pem, password=None)
        return (
            private.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )

    def issue(
        self,
        scope_ref: UUID,
        *,
        expires_at: datetime,
        issued_at: Optional[datetime] = None,
        jti: Optional[UUID] = None,
    ) -> IssuedDataToken:
        """
        Firma un token para un `scope_ref` ya materializado en Valkey.

        No resuelve el alcance ni escribe en Valkey: recibe el ref y la vigencia
        ya decididos. Mantener la firma ignorante del alcance es lo que garantiza
        que ningún dato de cliente pueda acabar en la carga útil por accidente.

        `jti` se puede imponer desde fuera para que el rastro forense se escriba
        con el mismo identificador que va firmado. Si se genera aquí y se
        guardase por separado, un fallo entre ambos pasos dejaría un rastro que
        no corresponde a ningún token.
        """
        now = issued_at or datetime.now(timezone.utc)
        if expires_at <= now:
            raise ValueError("expires_at debe ser posterior a la emisión")

        token_id = jti or uuid4()
        payload = {
            "jti": str(token_id),
            "scope_ref": str(scope_ref),
            "aud": settings.DATA_TOKEN_AUDIENCE,
            "iat": now.isoformat(),
            "nbf": now.isoformat(),
            "exp": expires_at.isoformat(),
        }

        token = pyseto.encode(
            key=self.key,
            payload=json.dumps(payload).encode("utf-8"),
            footer=json.dumps({"kid": settings.DATA_TOKEN_KEY_ID}).encode("utf-8"),
        )

        return IssuedDataToken(
            token=token.decode("utf-8"),
            jti=token_id,
            scope_ref=scope_ref,
            issued_at=now,
            expires_at=expires_at,
        )


def generate_ed25519_keypair_b64() -> tuple[str, str]:
    """
    Genera un par Ed25519 y lo devuelve como (privada_b64, publica_pem).

    Utilidad de operación: la privada va a `DATA_TOKEN_PRIVATE_KEY_B64` aquí y la
    pública a siscom-api. En base64 de una línea porque el despliegue escribe el
    .env con un heredoc, que rompe con PEM multilínea.
    """
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return (
        base64.b64encode(private_pem).decode("ascii"),
        public_pem.decode("ascii"),
    )
