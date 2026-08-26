"""El dinero nunca se representa en float."""

from decimal import Decimal

import pytest

from app.services import money


def test_parse_quantizes_to_cents():
    assert money.parse("1333.333") == Decimal("1333.33")
    assert money.parse(100) == Decimal("100.00")


def test_dump_always_has_two_decimals():
    assert money.dump(Decimal("150.5")) == "150.50"
    assert money.dump("174.58") == "174.58"


def test_cents_round_trip():
    assert money.to_cents("1546.66") == 154666
    assert money.from_cents(154666) == Decimal("1546.66")
    assert money.dump(money.from_cents(money.to_cents("0.03"))) == "0.03"


def test_float_is_rejected():
    with pytest.raises(money.MoneyError):
        money.parse(0.1)


def test_bool_is_rejected():
    """bool es subclase de int: sin esto, True se volvería 1.00."""
    with pytest.raises(money.MoneyError):
        money.parse(True)
