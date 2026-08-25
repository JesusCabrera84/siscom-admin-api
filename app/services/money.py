"""
Dinero: Decimal a dos centavos. `float` está prohibido.

JSON no tiene decimales: las cantidades salen como string ("1546.66") o como
enteros de centavos. Nunca como float, que no puede representar 0.01 y es el
origen clásico de cobrar de más o de menos.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


class MoneyError(ValueError):
    """Cantidad que no se puede tratar como dinero."""


def parse(value: Decimal | int | str) -> Decimal:
    """
    Normaliza a dos decimales con redondeo comercial (half-up).

    Acepta Decimal, int (pesos enteros) y string. Rechaza float a propósito:
    `Decimal(0.1)` no es 0.1, y `Decimal(str(0.1))` ya llega contaminado.
    """
    if isinstance(value, bool) or value is None:
        raise MoneyError("cantidad inválida")
    if isinstance(value, float):
        raise MoneyError(
            "el dinero no se representa en float: usa Decimal, int o string"
        )
    if isinstance(value, Decimal):
        raw = value
    elif isinstance(value, int):
        raw = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise MoneyError("cantidad vacía")
        raw = Decimal(text)
    else:
        raise MoneyError(f"tipo no soportado: {type(value).__name__}")
    return raw.quantize(CENTS, rounding=ROUND_HALF_UP)


def dump(value: Decimal | int | str) -> str:
    """Siempre dos decimales, listo para JSON o para mostrar."""
    return format(parse(value), "f")


def to_cents(value: Decimal | int | str) -> int:
    amount = parse(value)
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_cents(cents: int) -> Decimal:
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise MoneyError("los centavos deben ser int")
    return (Decimal(cents) / 100).quantize(CENTS, rounding=ROUND_HALF_UP)
