"""
Política única de montos y períodos de cobro.

Todo servicio que cobre una suscripción (Stripe, pago manual) debe calcular el
monto y las fechas del período con estas funciones, para que el importe cobrado,
la factura y la vigencia sean idénticos por cualquier vía.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Optional

from app.models.subscription import BillingCycle
from app.services import money

if TYPE_CHECKING:
    from app.models.plan import Plan

IVA_RATE = Decimal("0.16")
_CENTS = money.CENTS

MONTHLY_DAYS = 30
YEARLY_DAYS = 365


def cycle_duration(billing_cycle: str) -> timedelta:
    if billing_cycle.upper() == BillingCycle.YEARLY.value:
        return timedelta(days=YEARLY_DAYS)
    return timedelta(days=MONTHLY_DAYS)


def as_aware(ts: Optional[datetime]) -> Optional[datetime]:
    """Las columnas de período son TIMESTAMP sin zona; se leen como UTC."""
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def next_period(
    billing_cycle: str,
    *,
    now: datetime,
    current_end: Optional[datetime] = None,
) -> tuple[datetime, datetime]:
    """
    Fechas del período que acaba de pagarse.

    Una renovación anticipada del mismo plan se encadena al final de la vigencia
    en curso: el cliente nunca pierde los días que ya pagó. Si no hay vigencia
    (o ya venció), el período arranca en el momento del cobro.
    """
    start = now
    end_in_force = as_aware(current_end)
    if end_in_force is not None and end_in_force > now:
        start = end_in_force
    return start, start + cycle_duration(billing_cycle)


def with_iva(subtotal: Decimal | int | str) -> tuple[Decimal, Decimal, Decimal]:
    """
    Desglosa (subtotal, IVA, total) a dos decimales.

    El total se arma como subtotal + IVA redondeado, no como subtotal * 1.16,
    para que la factura cuadre exactamente con el importe cobrado.
    """
    base = money.parse(subtotal)
    tax = (base * IVA_RATE).quantize(_CENTS, rounding=ROUND_HALF_UP)
    return base, tax, base + tax


def to_cents(amount: Decimal | int | str) -> int:
    return money.to_cents(amount)


def quote_plan(plan: "Plan", billing_cycle: str) -> dict:
    """
    Cotización oficial de un plan. El cliente la muestra; nunca la calcula.

    Los importes van en string y en centavos enteros para que JSON no los
    convierta en float.
    """
    cycle = billing_cycle.upper()
    list_price = (
        plan.price_yearly if cycle == BillingCycle.YEARLY.value else plan.price_monthly
    )
    subtotal, tax, total = with_iva(list_price or 0)
    return {
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "plan_code": plan.code,
        "billing_cycle": cycle,
        "currency": "MXN",
        "subtotal": money.dump(subtotal),
        "tax": money.dump(tax),
        "total": money.dump(total),
        "amount_cents": money.to_cents(total),
    }
