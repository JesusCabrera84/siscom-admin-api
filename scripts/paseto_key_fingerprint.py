#!/usr/bin/env python3
"""
Huella de la clave PASETO efectiva, para comparar entornos sin mover secretos.

POR QUÉ NO BASTA CON HACER EL SHA DE LA VARIABLE
================================================
admin-api y siscom-api no derivan la clave igual: aquí el material se rellena
con ceros hasta 32 bytes (`ljust`) o se trunca, y allí no. Con la misma cadena de
configuración, un lado obtiene 21 bytes + 11 ceros y el otro 21 bytes: **huellas
distintas a partir de una clave idéntica**.

Por eso este script imprime la huella del material **efectivo** —los bytes que
realmente se pasan a `Key.new`— y no la de la cadena de configuración. Es lo
único comparable entre servicios, y es lo que decide si los tokens validan.

Equivale a `scripts/share_key_fingerprint.py` de siscom-api. Ejecutar los dos y
comparar contesta en un minuto si los dos entornos comparten clave.

Uso:
    python scripts/paseto_key_fingerprint.py

    # en producción, dentro del contenedor:
    docker exec -it siscom-admin-api python scripts/paseto_key_fingerprint.py

No imprime la clave ni ningún material del que pueda reconstruirse: solo los 12
primeros caracteres hexadecimales de su SHA-256.
"""

import base64
import binascii
import hashlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402

EXPECTED_BYTES = 32
FINGERPRINT_CHARS = 12


def _fingerprint(material: bytes) -> str:
    return hashlib.sha256(material).hexdigest()[:FINGERPRINT_CHARS]


def _describe(name: str, raw_value: str | None) -> int:
    """Imprime el diagnóstico de una clave. Devuelve 1 si hay algo que mirar."""
    print(f"\n{name}")
    print("-" * len(name))

    if not raw_value:
        print("  no configurada")
        return 0

    problems = 0

    # Cómo se decodifica, que es donde los dos servicios pueden divergir
    try:
        base64.b64decode(raw_value, validate=True)
        print("  base64 estricto        : OK")
    except (binascii.Error, ValueError):
        print(
            "  base64 estricto        : ❌ FALLA (el decode laxo descarta caracteres)"
        )
        problems += 1

    decoded = base64.b64decode(raw_value)
    print(f"  bytes tras decodificar : {len(decoded)}")

    # Material efectivo: exactamente lo que se le pasa a Key.new
    effective = decoded
    if len(effective) < EXPECTED_BYTES:
        effective = effective.ljust(EXPECTED_BYTES, b"\0")
        print(
            f"  ⚠️  rellenado con ceros hasta {EXPECTED_BYTES} bytes."
            f"\n      · entropía efectiva: la de {len(decoded)} bytes, no la de "
            f"{EXPECTED_BYTES}."
            f"\n      · un servicio que verifique SIN rellenar deriva una clave"
            f"\n        DISTINTA: los tokens no validan entre servicios aunque los"
            f"\n        dos tengan esta misma cadena configurada."
        )
        problems += 1
    elif len(effective) > EXPECTED_BYTES:
        effective = effective[:EXPECTED_BYTES]
        print(f"  ⚠️  truncado de {len(decoded)} a {EXPECTED_BYTES} bytes")
        problems += 1

    if not any(effective):
        print("  ❌ TODO CEROS: es el valor de .env.example. Cualquiera puede firmar.")
        problems += 1

    print(f"  huella del material efectivo : {_fingerprint(effective)}")
    return problems


def main() -> int:
    print("=" * 64)
    print("Huella de las claves PASETO efectivas — siscom-admin-api")
    print("=" * 64)
    print("\nCompara estas huellas con las del otro servicio:")
    print("  · IGUALES   -> misma cadena y misma derivación: el flujo funciona.")
    print("  · DISTINTAS -> las claves EFECTIVAS divergen y los tokens no validan,")
    print("                 pero NO deduzcas que el contenido configurado es distinto:")
    print(
        "                 si hay aviso de longitud, el relleno basta para explicarlo."
    )
    print("                 Los avisos de abajo dicen cuál de las dos cosas falló.")

    problems = _describe(
        "PASETO_SECRET_KEY (tokens de servicio internos)", settings.PASETO_SECRET_KEY
    )
    problems += _describe(
        "SHARE_LOCATION_KEY_B64 (compartir ubicación, heredado)",
        settings.SHARE_LOCATION_KEY_B64,
    )

    print()
    if problems:
        print(f"⚠️  {problems} aviso(s). Ver arriba.")
    else:
        print("✅ Sin avisos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
