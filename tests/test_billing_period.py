"""Política de montos y períodos: el cliente paga lo que ve y no pierde días."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.services import billing_period

NOW = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "subtotal,expected_tax,expected_total",
    [
        ("299.00", "47.84", "346.84"),
        ("2990.00", "478.40", "3468.40"),
        # 0.16 * 1333.33 = 213.3328 → redondeo a centavos
        ("1333.33", "213.33", "1546.66"),
        # IVA por debajo del centavo: no se inventa un cargo que no existe
        ("0.03", "0.00", "0.03"),
    ],
)
def test_with_iva_rounds_to_cents_and_total_is_the_sum(
    subtotal, expected_tax, expected_total
):
    base, tax, total = billing_period.with_iva(subtotal)
    assert base == Decimal(subtotal)
    assert tax == Decimal(expected_tax)
    assert total == Decimal(expected_total)
    assert total == base + tax


def test_to_cents_matches_the_two_decimal_total():
    _, _, total = billing_period.with_iva("1333.33")
    assert billing_period.to_cents(total) == 154666


def test_with_iva_accepts_decimal_int_and_str_alike():
    assert billing_period.with_iva(100) == billing_period.with_iva("100")
    assert billing_period.with_iva(Decimal("100")) == billing_period.with_iva("100.00")


def test_with_iva_rejects_float():
    """float no puede representar centavos; se rechaza para no cobrar mal."""
    from app.services.money import MoneyError

    with pytest.raises(MoneyError):
        billing_period.with_iva(0.1)


def test_quote_plan_exposes_strings_and_integer_cents():
    from uuid import uuid4

    from app.models.plan import Plan

    plan = Plan(
        id=uuid4(),
        name="Pro",
        code="pro",
        price_monthly=Decimal("1333.33"),
        price_yearly=Decimal("13333.00"),
        is_active=True,
    )
    quoted = billing_period.quote_plan(plan, "MONTHLY")
    assert quoted["subtotal"] == "1333.33"
    assert quoted["tax"] == "213.33"
    assert quoted["total"] == "1546.66"
    assert quoted["amount_cents"] == 154666
    assert isinstance(quoted["amount_cents"], int)


def test_first_payment_starts_the_period_today():
    start, end = billing_period.next_period("MONTHLY", now=NOW)
    assert start == NOW
    assert end == NOW + timedelta(days=30)


def test_early_renewal_chains_so_paid_days_are_not_lost():
    current_end = NOW + timedelta(days=4)
    start, end = billing_period.next_period("MONTHLY", now=NOW, current_end=current_end)
    assert start == current_end
    assert end == current_end + timedelta(days=30)


def test_expired_period_restarts_today_instead_of_backdating():
    start, end = billing_period.next_period(
        "MONTHLY", now=NOW, current_end=NOW - timedelta(days=5)
    )
    assert start == NOW
    assert end == NOW + timedelta(days=30)


def test_naive_period_end_is_read_as_utc():
    naive_end = (NOW + timedelta(days=4)).replace(tzinfo=None)
    start, _ = billing_period.next_period("MONTHLY", now=NOW, current_end=naive_end)
    assert start == NOW + timedelta(days=4)


def test_yearly_cycle_lasts_a_year():
    start, end = billing_period.next_period("yearly", now=NOW)
    assert end - start == timedelta(days=365)
