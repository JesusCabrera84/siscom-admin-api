"""
Renovación automática de suscripciones.

POLÍTICA
========
El cobro se intenta 3 días antes de vencer. Cobrar con anticipación deja margen
para reintentar y avisar antes de que el cliente pierda el servicio, y no le
regala días: el período nuevo se encadena al final de la vigencia en curso
(ver `billing_period.next_period`).

Si el cobro falla, la suscripción pasa a PAST_DUE y sigue operando hasta 7 días
después del vencimiento. Un rechazo temporal del banco es mucho más común que un
cliente que no quiere pagar, y cortarle el servicio a alguien con saldo
insuficiente de un día es peor negocio que esperar. Se reintenta a los días 1, 3
y 5 desde el primer intento; agotados los reintentos no se hace nada más: al
vencer la gracia la suscripción deja de estar activa por sí sola, sin que nadie
tenga que ejecutar un proceso de corte.

Un rechazo que pide 3DS no consume reintentos de la misma forma: el cargo no se
puede autorizar sin el cliente presente, así que se deja el intento abierto para
que lo autorice desde el panel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.locks import advisory_xact_lock
from app.models.subscription import Subscription, SubscriptionStatus
from app.services import billing_period
from app.services.gateways.stripe_gateway import (
    RENEWAL_ACTION_REQUIRED,
    RENEWAL_DECLINED,
    RENEWAL_NO_CARD,
    RENEWAL_OK,
    RENEWAL_UNAVAILABLE,
    StripeGateway,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    """
    Reloj del servicio, siempre con zona.

    Las fechas de vigencia y de dunning viven en columnas de tipos distintos
    (unas con zona y otras sin ella); trabajar todo en UTC con zona evita
    comparar naive contra aware al mezclarlas.
    """
    return datetime.now(timezone.utc)


#: Cuánto antes del vencimiento se intenta el primer cobro.
CHARGE_LEAD_DAYS = 3

#: Días de servicio después del vencimiento mientras se reintenta el cobro.
GRACE_DAYS = 7

#: Días desde el primer intento en que se vuelve a intentar.
RETRY_SCHEDULE_DAYS = (1, 3, 5)

#: Tope de suscripciones por corrida, para que una corrida no se eternice.
DEFAULT_BATCH_LIMIT = 200


@dataclass
class RenewalOutcome:
    subscription_id: UUID
    result: str
    detail: str = ""


@dataclass
class RenewalRun:
    renewed: list[UUID] = field(default_factory=list)
    action_required: list[UUID] = field(default_factory=list)
    retry_scheduled: list[UUID] = field(default_factory=list)
    exhausted: list[UUID] = field(default_factory=list)
    skipped: list[UUID] = field(default_factory=list)
    outcomes: list[RenewalOutcome] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "renewed": len(self.renewed),
            "action_required": len(self.action_required),
            "retry_scheduled": len(self.retry_scheduled),
            "exhausted": len(self.exhausted),
            "skipped": len(self.skipped),
            "details": [
                {
                    "subscription_id": str(o.subscription_id),
                    "result": o.result,
                    "detail": o.detail,
                }
                for o in self.outcomes
            ],
        }


def due_subscriptions(
    db: Session, *, now: Optional[datetime] = None, limit: int = DEFAULT_BATCH_LIMIT
) -> list[Subscription]:
    """
    Suscripciones a las que toca intentarles el cobro en esta corrida.

    Se excluyen las que ya tienen un reintento agendado a futuro: sin eso, cada
    corrida del cron reintentaría el mismo cobro rechazado.
    """
    now = billing_period.as_aware(now) or _now()
    horizon = now + timedelta(days=CHARGE_LEAD_DAYS)
    return (
        db.query(Subscription)
        .filter(
            Subscription.auto_renew.is_(True),
            Subscription.status.in_(
                [
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.PAST_DUE.value,
                ]
            ),
            Subscription.expires_at.isnot(None),
            Subscription.expires_at <= horizon,
            or_(
                Subscription.dunning_next_attempt.is_(None),
                Subscription.dunning_next_attempt <= now,
            ),
            or_(
                Subscription.grace_until.is_(None),
                Subscription.grace_until > now,
            ),
        )
        .order_by(Subscription.expires_at.asc())
        .limit(limit)
        .all()
    )


def _still_due(sub: Subscription, now: datetime) -> bool:
    """Revalida bajo el lock: otra corrida pudo haberla renovado ya."""
    if not sub.auto_renew:
        return False
    if sub.status not in (
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.PAST_DUE.value,
    ):
        return False
    expires = billing_period.as_aware(sub.expires_at)
    if expires is None or expires > now + timedelta(days=CHARGE_LEAD_DAYS):
        return False
    next_attempt = billing_period.as_aware(sub.dunning_next_attempt)
    if next_attempt is not None and next_attempt > now:
        return False
    grace = billing_period.as_aware(sub.grace_until)
    if grace is not None and grace <= now:
        return False
    return True


def _mark_renewed(sub: Subscription, now: datetime) -> None:
    sub.status = SubscriptionStatus.ACTIVE.value
    sub.grace_until = None
    sub.dunning_attempt_count = 0
    sub.dunning_last_attempt = now
    sub.dunning_next_attempt = None
    sub.renewal_last_error = None
    sub.updated_at = now


def _mark_failed(sub: Subscription, now: datetime, error: str) -> str:
    """
    Registra el intento fallido y agenda el siguiente.

    La gracia se calcula desde el vencimiento, no desde el intento, para que
    reintentar no la vaya empujando hacia adelante indefinidamente.
    """
    attempts = (sub.dunning_attempt_count or 0) + 1
    sub.dunning_attempt_count = attempts
    sub.dunning_last_attempt = now
    sub.renewal_last_error = error[:500] if error else None
    sub.status = SubscriptionStatus.PAST_DUE.value
    sub.updated_at = now

    expires = billing_period.as_aware(sub.expires_at) or now
    sub.grace_until = expires + timedelta(days=GRACE_DAYS)

    if attempts <= len(RETRY_SCHEDULE_DAYS):
        offset = RETRY_SCHEDULE_DAYS[attempts - 1]
        previous = RETRY_SCHEDULE_DAYS[attempts - 2] if attempts > 1 else 0
        sub.dunning_next_attempt = now + timedelta(days=offset - previous)
        return "retry_scheduled"

    sub.dunning_next_attempt = None
    return "exhausted"


def _renew_one(
    db: Session, gateway: StripeGateway, subscription_id: UUID, now: datetime
) -> RenewalOutcome:
    """
    Cobra una suscripción en su propia transacción.

    Cada suscripción se aísla a propósito: un error en una no puede dejar a las
    demás sin cobrar ni contaminar su estado.
    """
    advisory_xact_lock(db, "renew", str(subscription_id))
    sub = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id)
        .with_for_update()
        .first()
    )
    if sub is None:
        return RenewalOutcome(subscription_id, "skipped", "no existe")
    if not _still_due(sub, now):
        return RenewalOutcome(subscription_id, "skipped", "ya no aplica")

    attempt = (sub.dunning_attempt_count or 0) + 1
    result = gateway.charge_renewal(db, sub, attempt)
    status = result.get("status")
    error = result.get("error") or ""

    if status == RENEWAL_OK:
        _mark_renewed(sub, now)
        return RenewalOutcome(subscription_id, "renewed", "")

    if status == RENEWAL_ACTION_REQUIRED:
        # No consume reintentos: el cargo espera al cliente, no al banco.
        sub.status = SubscriptionStatus.PAST_DUE.value
        sub.renewal_last_error = error[:500]
        sub.dunning_last_attempt = now
        expires = billing_period.as_aware(sub.expires_at) or now
        sub.grace_until = expires + timedelta(days=GRACE_DAYS)
        sub.dunning_next_attempt = now + timedelta(days=1)
        sub.updated_at = now
        return RenewalOutcome(subscription_id, "action_required", error)

    if status in (RENEWAL_DECLINED, RENEWAL_NO_CARD, RENEWAL_UNAVAILABLE):
        outcome = _mark_failed(sub, now, error)
        return RenewalOutcome(subscription_id, outcome, error)

    return RenewalOutcome(subscription_id, "skipped", f"estado inesperado: {status}")


def run_renewals(
    db: Session,
    *,
    now: Optional[datetime] = None,
    limit: int = DEFAULT_BATCH_LIMIT,
    gateway: Optional[StripeGateway] = None,
) -> RenewalRun:
    """
    Corre el ciclo de renovación. Pensada para ejecutarse desde un cron.

    Es segura de ejecutar varias veces al día: la llave de idempotencia por
    período renovado evita cobrar dos veces y los reintentos agendados evitan
    machacar una tarjeta rechazada.
    """
    now = billing_period.as_aware(now) or _now()
    gw = gateway or StripeGateway()
    run = RenewalRun()

    pending = [s.id for s in due_subscriptions(db, now=now, limit=limit)]
    logger.info("Renovación: %s suscripciones por cobrar", len(pending))

    for subscription_id in pending:
        try:
            outcome = _renew_one(db, gw, subscription_id, now)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Renovación falló para suscripción %s", subscription_id)
            outcome = RenewalOutcome(subscription_id, "skipped", "error interno")

        run.outcomes.append(outcome)
        buckets = {
            "renewed": run.renewed,
            "action_required": run.action_required,
            "retry_scheduled": run.retry_scheduled,
            "exhausted": run.exhausted,
        }
        buckets.get(outcome.result, run.skipped).append(subscription_id)

    logger.info("Renovación terminada: %s", run.as_dict())
    return run
