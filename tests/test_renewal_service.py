"""Renovación automática: cobro anticipado, dunning, gracia, 3DS e idempotencia."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import stripe

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.payment_gateway_customer import PaymentGatewayCustomer
from app.models.payment_method import PaymentMethod
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.services import billing_period, renewal_service, subscription_query
from app.services.gateways.stripe_gateway import GATEWAY, StripeGateway
from app.services.gateways.stripe_gateway import stripe as stripe_mod


def utcnow():
    """El gateway escribe fechas con zona; las pruebas usan la misma convención."""
    return datetime.now(timezone.utc)


MONTHLY_BASE = Decimal("299.00")
MONTHLY_TOTAL = billing_period.with_iva(MONTHLY_BASE)[2]
MONTHLY_CENTS = billing_period.to_cents(MONTHLY_TOTAL)


class FakePI:
    def __init__(self, *, id="pi_renew", status="succeeded", amount=MONTHLY_CENTS):
        self.id = id
        self.status = status
        self.amount = amount
        self.client_secret = "cs_renew"
        self.metadata = {}
        self.charges = {
            "data": [{"payment_method_details": {"card": {"brand": "visa"}}}]
        }
        self.latest_charge = None

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "amount": self.amount,
            "metadata": self.metadata,
            "charges": self.charges,
        }


def _card_error(code):
    """Reproduce la forma del error de Stripe: e.error.code y e.error.payment_intent."""
    err = stripe.error.CardError("Tarjeta rechazada", None, code)
    err.error = type(
        "Err", (), {"code": code, "payment_intent": {"id": "pi_declined"}}
    )()
    return err


@pytest.fixture
def gw(monkeypatch):
    monkeypatch.setattr(stripe_mod, "api_key", "sk_test", raising=False)
    return StripeGateway()


def _plan(db) -> Plan:
    plan = Plan(
        id=uuid4(),
        name=f"Plan {uuid4().hex[:8]}",
        code=f"pro-{uuid4().hex[:8]}",
        price_monthly=MONTHLY_BASE,
        price_yearly=Decimal("2990.00"),
        is_active=True,
    )
    db.add(plan)
    db.commit()
    return plan


def _card(db, account, *, default=True) -> PaymentMethod:
    pm = PaymentMethod(
        account_id=account.id,
        gateway=GATEWAY,
        external_token=f"pm_{uuid4().hex[:10]}",
        payment_method_type="card",
        brand="visa",
        last4="4242",
        is_default=default,
        is_active=True,
    )
    db.add(pm)
    db.add(
        PaymentGatewayCustomer(
            account_id=account.id,
            gateway=GATEWAY,
            external_customer_id=f"cus_{uuid4().hex[:10]}",
        )
    )
    db.commit()
    return pm


def _subscription(db, org, plan, *, days_left=2, auto_renew=True) -> Subscription:
    now = utcnow()
    expires = now + timedelta(days=days_left)
    sub = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        started_at=now - timedelta(days=28),
        expires_at=expires,
        current_period_start=now - timedelta(days=28),
        current_period_end=expires,
        billing_cycle="MONTHLY",
        auto_renew=auto_renew,
    )
    db.add(sub)
    db.commit()
    return sub


def _ready(db, account, org, monkeypatch):
    plan = _plan(db)
    _card(db, account)
    sub = _subscription(db, org, plan)
    return plan, sub


# ── Selección ────────────────────────────────────────────────────────────────


def test_only_subscriptions_inside_the_lead_window_are_charged(
    db_session, test_account_data, test_organization_data
):
    plan = _plan(db_session)
    soon = _subscription(db_session, test_organization_data, plan, days_left=2)
    _subscription(db_session, test_organization_data, plan, days_left=20)

    due = renewal_service.due_subscriptions(db_session)

    assert [s.id for s in due] == [soon.id]


def test_auto_renew_off_is_never_charged(
    db_session, test_account_data, test_organization_data
):
    plan = _plan(db_session)
    _subscription(db_session, test_organization_data, plan, auto_renew=False)

    assert renewal_service.due_subscriptions(db_session) == []


def test_a_scheduled_retry_is_not_attempted_early(
    db_session, test_account_data, test_organization_data
):
    """Sin esto, cada corrida del cron machacaría la misma tarjeta rechazada."""
    plan = _plan(db_session)
    sub = _subscription(db_session, test_organization_data, plan)
    sub.dunning_next_attempt = utcnow() + timedelta(days=1)
    db_session.commit()

    assert renewal_service.due_subscriptions(db_session) == []


def test_expired_grace_stops_being_charged(
    db_session, test_account_data, test_organization_data
):
    plan = _plan(db_session)
    sub = _subscription(db_session, test_organization_data, plan, days_left=-10)
    sub.status = SubscriptionStatus.PAST_DUE.value
    sub.grace_until = utcnow() - timedelta(days=1)
    db_session.commit()

    assert renewal_service.due_subscriptions(db_session) == []


# ── Cobro exitoso ────────────────────────────────────────────────────────────


def test_successful_renewal_chains_the_period_and_clears_dunning(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    original_end = billing_period.as_aware(sub.expires_at)
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakePI()

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)

    run = renewal_service.run_renewals(db_session, gateway=gw)

    db_session.refresh(sub)
    assert run.as_dict()["renewed"] == 1
    assert captured["off_session"] is True
    assert captured["confirm"] is True
    assert captured["amount"] == MONTHLY_CENTS
    # Cobrar 3 días antes no puede costarle días al cliente.
    assert billing_period.as_aware(sub.expires_at) == original_end + timedelta(days=30)
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.dunning_attempt_count == 0
    assert sub.grace_until is None
    assert sub.renewal_last_error is None


def test_renewal_charges_iva_and_leaves_a_paid_invoice(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", lambda **k: FakePI())

    renewal_service.run_renewals(db_session, gateway=gw)

    payment = db_session.query(Payment).one()
    invoice = db_session.query(Invoice).filter(Invoice.id == payment.invoice_id).one()
    assert payment.payment_status == PaymentStatus.SUCCESS.value
    assert payment.amount == MONTHLY_TOTAL
    assert invoice.invoice_status == InvoiceStatus.PAID.value
    assert invoice.subtotal == MONTHLY_BASE
    assert invoice.tax_amount + invoice.subtotal == invoice.total_amount


def test_running_the_cron_twice_charges_only_once(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs["idempotency_key"])
        return FakePI()

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)

    renewal_service.run_renewals(db_session, gateway=gw)
    renewal_service.run_renewals(db_session, gateway=gw)

    assert len(calls) == 1
    assert db_session.query(Payment).count() == 1


# ── Cobro rechazado ──────────────────────────────────────────────────────────


def test_declined_card_keeps_the_service_during_grace(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    expires = billing_period.as_aware(sub.expires_at)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **k: (_ for _ in ()).throw(_card_error("card_declined")),
    )

    run = renewal_service.run_renewals(db_session, gateway=gw)

    db_session.refresh(sub)
    assert run.as_dict()["retry_scheduled"] == 1
    assert sub.status == SubscriptionStatus.PAST_DUE.value
    assert sub.dunning_attempt_count == 1
    assert billing_period.as_aware(sub.grace_until) == expires + timedelta(
        days=renewal_service.GRACE_DAYS
    )
    # Sigue operando: es la razón de existir de la gracia.
    assert subscription_query.has_active_subscription(
        db_session, test_organization_data.id
    )
    assert sub.is_active() is True


def test_grace_does_not_drift_forward_with_each_retry(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Anclar la gracia al vencimiento evita regalar servicio indefinidamente."""
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    expires = billing_period.as_aware(sub.expires_at)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **k: (_ for _ in ()).throw(_card_error("card_declined")),
    )

    for _ in range(3):
        sub.dunning_next_attempt = None
        db_session.commit()
        renewal_service.run_renewals(db_session, gateway=gw)
        db_session.refresh(sub)

    assert sub.dunning_attempt_count == 3
    assert billing_period.as_aware(sub.grace_until) == expires + timedelta(
        days=renewal_service.GRACE_DAYS
    )


def test_retries_run_out_and_the_subscription_lapses_by_itself(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **k: (_ for _ in ()).throw(_card_error("card_declined")),
    )

    for _ in range(len(renewal_service.RETRY_SCHEDULE_DAYS) + 1):
        sub.dunning_next_attempt = None
        db_session.commit()
        run = renewal_service.run_renewals(db_session, gateway=gw)
        db_session.refresh(sub)

    assert run.as_dict()["exhausted"] == 1
    assert sub.dunning_next_attempt is None

    # Al vencer la gracia deja de estar activa sin que corra ningún proceso.
    sub.grace_until = utcnow() - timedelta(minutes=1)
    sub.expires_at = utcnow() - timedelta(days=1)
    db_session.commit()
    assert (
        subscription_query.get_primary_active_subscription(
            db_session, test_organization_data.id
        )
        is None
    )
    assert sub.is_active() is False


def test_each_retry_uses_a_new_stripe_key(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Repetir la llave devolvería el rechazo cacheado y jamás se podría cobrar."""
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    keys = []

    def fake_create(**kwargs):
        keys.append(kwargs["idempotency_key"])
        raise _card_error("card_declined")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda *_a, **_k: FakePI(status="canceled"),
    )

    for _ in range(2):
        sub.dunning_next_attempt = None
        db_session.commit()
        renewal_service.run_renewals(db_session, gateway=gw)
        db_session.refresh(sub)

    assert len(keys) == 2
    assert keys[0] != keys[1]
    # Un solo pago por período renovado, reusado entre intentos.
    assert db_session.query(Payment).count() == 1


def test_missing_card_marks_past_due_without_calling_stripe(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    sub = _subscription(db_session, test_organization_data, plan)

    def explode(**_kwargs):
        raise AssertionError("no debe llamarse a Stripe sin tarjeta")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", explode)

    renewal_service.run_renewals(db_session, gateway=gw)

    db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.PAST_DUE.value
    assert "tarjeta" in (sub.renewal_last_error or "").lower()


# ── 3DS ──────────────────────────────────────────────────────────────────────


def test_authentication_required_waits_for_the_customer(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **k: (_ for _ in ()).throw(_card_error("authentication_required")),
    )

    run = renewal_service.run_renewals(db_session, gateway=gw)

    db_session.refresh(sub)
    payment = db_session.query(Payment).one()
    assert run.as_dict()["action_required"] == 1
    assert payment.payment_status == PaymentStatus.REQUIRES_ACTION.value
    assert payment.gateway_payment_id == "pi_declined"
    assert sub.status == SubscriptionStatus.PAST_DUE.value
    # No consume reintentos: el pendiente es del cliente, no del banco.
    assert sub.dunning_attempt_count == 0
    assert sub.is_active() is True


def test_a_pending_3ds_intent_is_never_charged_twice(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """
    Si el cliente autoriza el cargo justo antes del reintento, emitir un segundo
    PaymentIntent le cobraría dos veces.
    """
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **k: (_ for _ in ()).throw(_card_error("authentication_required")),
    )
    renewal_service.run_renewals(db_session, gateway=gw)

    original_end = billing_period.as_aware(sub.expires_at)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda *_a, **_k: FakePI(id="pi_declined", status="succeeded"),
    )

    def explode(**_kwargs):
        raise AssertionError("no debe emitirse un segundo cargo")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", explode)

    sub.dunning_next_attempt = None
    db_session.commit()
    run = renewal_service.run_renewals(db_session, gateway=gw)

    db_session.refresh(sub)
    payment = db_session.query(Payment).one()
    assert run.as_dict()["renewed"] == 1
    assert payment.payment_status == PaymentStatus.SUCCESS.value
    assert billing_period.as_aware(sub.expires_at) == original_end + timedelta(days=30)


def test_unverifiable_prior_intent_does_not_issue_a_second_charge(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **k: (_ for _ in ()).throw(_card_error("authentication_required")),
    )
    renewal_service.run_renewals(db_session, gateway=gw)

    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda *_a, **_k: (_ for _ in ()).throw(
            stripe.error.APIConnectionError("caído")
        ),
    )

    def explode(**_kwargs):
        raise AssertionError("no debe emitirse un cargo sin verificar el anterior")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", explode)

    sub.dunning_next_attempt = None
    db_session.commit()
    run = renewal_service.run_renewals(db_session, gateway=gw)

    assert run.as_dict()["retry_scheduled"] == 1
    assert db_session.query(Payment).count() == 1


# ── Aislamiento ──────────────────────────────────────────────────────────────


def test_an_interactive_checkout_does_not_cancel_a_renewal_in_flight(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """
    El checkout cancela intentos abandonados de la cuenta. Un cobro de
    renovación no es uno de ellos: cancelarlo dejaría la suscripción sin cobrar.
    """
    plan, sub = _ready(
        db_session, test_account_data, test_organization_data, monkeypatch
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **k: FakePI(id="pi_renew_flight", status="processing"),
    )
    renewal_service.run_renewals(db_session, gateway=gw)

    renewal_payment = db_session.query(Payment).one()
    assert renewal_payment.payment_status == PaymentStatus.PROCESSING.value

    canceled = []
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "cancel",
        lambda pid, *_a, **_k: canceled.append(pid),
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent, "create", lambda **k: FakePI(id="pi_interactive")
    )
    gw.create_payment_intent(db_session, test_organization_data.id, plan.id, "MONTHLY")

    db_session.refresh(renewal_payment)
    assert "pi_renew_flight" not in canceled
    assert renewal_payment.payment_status == PaymentStatus.PROCESSING.value


def test_one_broken_subscription_does_not_block_the_others(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _card(db_session, test_account_data)
    broken = _subscription(db_session, test_organization_data, plan, days_left=1)
    healthy = _subscription(db_session, test_organization_data, plan, days_left=2)

    def fake_create(**kwargs):
        if kwargs["metadata"]["subscription_id"] == str(broken.id):
            raise RuntimeError("falla inesperada")
        return FakePI()

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)

    run = renewal_service.run_renewals(db_session, gateway=gw)

    db_session.refresh(healthy)
    assert healthy.id in run.renewed
    assert broken.id in run.skipped
