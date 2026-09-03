"""
Tests de la emisión del data token (PASETO v4.public).

Fijan las dos propiedades que hacen que este diseño cumpla el requisito de que
siscom-api no sepa nada de clientes:

1. La carga útil no contiene identidad de ningún tipo.
2. Quien verifica (con la pública) no puede firmar.
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pyseto
import pytest
from pyseto import Key

from app.utils.data_token import (
    DataTokenIssuer,
    DataTokenKeyNotConfigured,
    compute_expiry,
    generate_ed25519_keypair_b64,
)


@pytest.fixture
def keypair():
    return generate_ed25519_keypair_b64()


@pytest.fixture
def issuer(monkeypatch, keypair):
    private_b64, _public_pem = keypair
    monkeypatch.setattr(
        "app.utils.data_token.settings.DATA_TOKEN_PRIVATE_KEY_B64", private_b64
    )
    return DataTokenIssuer()


def _decode_with_public(public_pem: str, token: str) -> dict:
    verifier = Key.new(version=4, purpose="public", key=public_pem.encode("ascii"))
    return json.loads(pyseto.decode(keys=verifier, token=token).payload)


# ---------------------------------------------------------------------------
# Carga útil: lo que NO lleva es la propiedad importante
# ---------------------------------------------------------------------------


def test_payload_contains_exactly_the_agreed_claims(issuer, keypair):
    scope_ref = uuid4()
    now = datetime.now(timezone.utc)
    issued = issuer.issue(scope_ref, expires_at=now + timedelta(minutes=10))

    payload = _decode_with_public(keypair[1], issued.token)
    assert set(payload) == {"jti", "scope_ref", "aud", "iat", "nbf", "exp"}
    assert payload["scope_ref"] == str(scope_ref)
    assert payload["aud"] == "siscom-api"
    assert UUID(payload["jti"]) == issued.jti


def test_payload_carries_no_client_identity(issuer, keypair):
    """
    El token va firmado pero NO cifrado en v4.public: cualquiera que lo tenga lee
    la carga útil. Que no haya identidad no es una convención, es estructural.
    """
    issued = issuer.issue(
        uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    raw = json.dumps(_decode_with_public(keypair[1], issued.token)).lower()

    for forbidden in ("user", "organization", "account", "email", "device", "imei"):
        assert forbidden not in raw


def test_token_is_a_v4_public_token(issuer):
    issued = issuer.issue(
        uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    assert issued.token.startswith("v4.public.")


def test_footer_carries_the_key_id(issuer, monkeypatch):
    monkeypatch.setattr("app.utils.data_token.settings.DATA_TOKEN_KEY_ID", "v7")
    issued = issuer.issue(
        uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    footer = issued.token.rsplit(".", 1)[-1]
    import base64

    decoded = base64.urlsafe_b64decode(footer + "=" * (-len(footer) % 4))
    assert json.loads(decoded) == {"kid": "v7"}


def test_each_issuance_gets_a_fresh_jti(issuer):
    exp = datetime.now(timezone.utc) + timedelta(minutes=10)
    scope_ref = uuid4()
    assert (
        issuer.issue(scope_ref, expires_at=exp).jti
        != issuer.issue(scope_ref, expires_at=exp).jti
    )


# ---------------------------------------------------------------------------
# Asimetría: el verificador no puede firmar
# ---------------------------------------------------------------------------


def test_public_key_verifies_but_cannot_sign(issuer, keypair):
    """La propiedad que elimina la escalada del ADR-004."""
    public_pem = keypair[1]
    issued = issuer.issue(
        uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    # Verificar sí
    assert _decode_with_public(public_pem, issued.token)

    # Firmar no: pyseto rechaza una clave pública en encode
    verifier = Key.new(version=4, purpose="public", key=public_pem.encode("ascii"))
    with pytest.raises(ValueError):
        pyseto.encode(key=verifier, payload=b"{}")


def test_exported_public_key_matches_the_signing_key(issuer):
    """La pública se deriva de la privada, así que no puede desincronizarse."""
    issued = issuer.issue(
        uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    assert _decode_with_public(issuer.public_key_pem(), issued.token)


def test_a_different_key_cannot_verify(issuer):
    other_public = generate_ed25519_keypair_b64()[1]
    issued = issuer.issue(
        uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    with pytest.raises(pyseto.VerifyError):
        _decode_with_public(other_public, issued.token)


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------


def test_missing_key_fails_at_use_not_at_boot(monkeypatch):
    monkeypatch.setattr(
        "app.utils.data_token.settings.DATA_TOKEN_PRIVATE_KEY_B64", None
    )
    unconfigured = DataTokenIssuer()  # no revienta: la API debe poder arrancar

    assert not unconfigured.is_configured
    with pytest.raises(DataTokenKeyNotConfigured):
        unconfigured.issue(
            uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
        )


@pytest.mark.parametrize(
    "bad_key",
    ["no-es-base64!!", "aGVsbG8=", ""],
    ids=["no-base64", "base64-sin-pem", "vacia"],
)
def test_invalid_key_is_rejected(monkeypatch, bad_key):
    monkeypatch.setattr(
        "app.utils.data_token.settings.DATA_TOKEN_PRIVATE_KEY_B64", bad_key
    )
    if bad_key == "":
        # Cadena vacía es "no configurada", no "inválida"
        assert not DataTokenIssuer().is_configured
    else:
        with pytest.raises(ValueError):
            DataTokenIssuer()


def test_rsa_key_is_rejected(monkeypatch):
    """v4.public es Ed25519; cualquier otra curva o algoritmo debe fallar."""
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_pem = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    ).private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    monkeypatch.setattr(
        "app.utils.data_token.settings.DATA_TOKEN_PRIVATE_KEY_B64",
        base64.b64encode(rsa_pem).decode(),
    )
    with pytest.raises(ValueError, match="Ed25519"):
        DataTokenIssuer()


def test_expiry_in_the_past_is_rejected(issuer):
    with pytest.raises(ValueError):
        issuer.issue(
            uuid4(), expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
        )


# ---------------------------------------------------------------------------
# TTL adaptativo
# ---------------------------------------------------------------------------


def test_uses_the_full_ttl_when_the_scope_has_no_boundary():
    now = datetime.now(timezone.utc)
    assert compute_expiry(
        now, max_ttl_seconds=600, min_ttl_seconds=30
    ) == now + timedelta(seconds=600)


def test_a_closing_window_shortens_the_token():
    """Una ventana de team que cierra antes manda sobre el TTL máximo."""
    now = datetime.now(timezone.utc)
    boundary = now + timedelta(minutes=3)
    assert (
        compute_expiry(
            now, next_scope_boundary=boundary, max_ttl_seconds=600, min_ttl_seconds=30
        )
        == boundary
    )


def test_a_distant_boundary_does_not_extend_the_token():
    now = datetime.now(timezone.utc)
    assert compute_expiry(
        now,
        next_scope_boundary=now + timedelta(hours=5),
        max_ttl_seconds=600,
        min_ttl_seconds=30,
    ) == now + timedelta(seconds=600)


def test_an_imminent_boundary_is_floored():
    """Un token de cuatro segundos no le sirve a nadie."""
    now = datetime.now(timezone.utc)
    assert compute_expiry(
        now,
        next_scope_boundary=now + timedelta(seconds=4),
        max_ttl_seconds=600,
        min_ttl_seconds=30,
    ) == now + timedelta(seconds=30)


def test_a_boundary_already_past_is_floored_too():
    now = datetime.now(timezone.utc)
    assert compute_expiry(
        now,
        next_scope_boundary=now - timedelta(minutes=1),
        max_ttl_seconds=600,
        min_ttl_seconds=30,
    ) == now + timedelta(seconds=30)
