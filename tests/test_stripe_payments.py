"""Hardening de cobros Stripe: anti-doble-cobro, webhooks atómicos, idempotencia HTTP."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import stripe
from fastapi import HTTPException

from app.models.enums.gateway_event_status import GatewayEventStatus
from app.models.idempotency import ApiIdempotencyRequest
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.payment_gateway_customer import PaymentGatewayCustomer
from app.models.payment_gateway_event import PaymentGatewayEvent
from app.models.payment_method import PaymentMethod
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.services import billing_period
from app.services.gateways.stripe_gateway import GATEWAY, StripeGateway
from app.services.gateways.stripe_gateway import stripe as stripe_mod

MONTHLY_BASE = Decimal("299.00")
MONTHLY_TOTAL = billing_period.with_iva(MONTHLY_BASE)[2]
MONTHLY_CENTS = billing_period.to_cents(MONTHLY_TOTAL)


class FakePI:
    def __init__(
        self,
        *,
        id="pi_1",
        status="requires_payment_method",
        client_secret="cs_test",
        amount=MONTHLY_CENTS,
        metadata=None,
        charges=None,
        latest_charge=None,
    ):
        self.id = id
        self.status = status
        self.client_secret = client_secret
        self.amount = amount
        self.metadata = metadata or {}
        self.charges = charges or {"data": []}
        self.latest_charge = latest_charge

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "amount": self.amount,
            "metadata": self.metadata,
            "charges": self.charges,
            "latest_charge": self.latest_charge,
        }


class FakeEvent:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self):
        return self._payload


def _plan(db, *, monthly="299.00", yearly="2990.00") -> Plan:
    plan = Plan(
        id=uuid4(),
        name=f"Plan {uuid4().hex[:8]}",
        code=f"pro-{uuid4().hex[:8]}",
        price_monthly=Decimal(monthly),
        price_yearly=Decimal(yearly),
        is_active=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _customer(db, account) -> PaymentGatewayCustomer:
    rec = PaymentGatewayCustomer(
        account_id=account.id,
        gateway=GATEWAY,
        external_customer_id="cus_test_123",
    )
    db.add(rec)
    db.commit()
    return rec


def _invoice_payment(db, account, org, plan, *, pi_id, status, cycle="MONTHLY"):
    gw = StripeGateway()
    period = gw._period_bucket(cycle)
    idem = gw._idem_key("pi", str(account.id), str(plan.id), cycle, period)
    list_price = plan.price_yearly if cycle == "YEARLY" else plan.price_monthly
    subtotal, tax, total = billing_period.with_iva(list_price)
    invoice = Invoice(
        account_id=account.id,
        organization_id=org.id,
        invoice_number=f"INV-TEST-{uuid4().hex[:8]}",
        invoice_status=InvoiceStatus.OPEN.value,
        subtotal=subtotal,
        discount_amount=Decimal("0"),
        tax_amount=tax,
        total_amount=total,
        currency="MXN",
    )
    db.add(invoice)
    db.flush()
    payment = Payment(
        invoice_id=invoice.id,
        account_id=account.id,
        organization_id=org.id,
        gateway=GATEWAY,
        gateway_payment_id=pi_id,
        idempotency_key=idem,
        payment_method_type="card",
        payment_method_meta={},
        amount=total,
        currency="MXN",
        refunded_amount=Decimal("0"),
        payment_status=status,
        extra_data={"plan_id": str(plan.id), "billing_cycle": cycle},
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    db.refresh(invoice)
    return invoice, payment


def _succeeded_event(payment, org, plan, event_id="evt_1"):
    return {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "created": 1,
        "livemode": False,
        "data": {
            "object": {
                "id": payment.gateway_payment_id,
                "status": "succeeded",
                "amount": 29900,
                "metadata": {
                    "organization_id": str(org.id),
                    "plan_id": str(plan.id),
                    "billing_cycle": "MONTHLY",
                },
                "charges": {
                    "data": [{"payment_method_details": {"card": {"brand": "visa"}}}]
                },
            }
        },
    }


def _charge_event(payment, *, event_id, amount_refunded, refunded):
    return {
        "id": event_id,
        "type": "charge.refunded",
        "created": 1,
        "livemode": False,
        "data": {
            "object": {
                "id": "ch_1",
                "payment_intent": payment.gateway_payment_id,
                "amount": MONTHLY_CENTS,
                "amount_refunded": amount_refunded,
                "refunded": refunded,
            }
        },
    }


def _dispute_event(payment, *, event_id, event_type, status, due_by=None):
    return {
        "id": event_id,
        "type": event_type,
        "created": 1,
        "livemode": False,
        "data": {
            "object": {
                "id": "dp_1",
                "payment_intent": payment.gateway_payment_id,
                "charge": "ch_1",
                "amount": MONTHLY_CENTS,
                "reason": "fraudulent",
                "status": status,
                "evidence_details": {"due_by": due_by},
            }
        },
    }


def _feed_events(monkeypatch, *events):
    """Encadena eventos en construct_event, uno por llamada a handle_webhook."""
    queue = iter(events)
    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(next(queue)),
    )


def _paid_subscription(db, account, org, plan, gw_, monkeypatch, *, pi_id, event_id):
    """Deja un pago cumplido con su suscripción activa, como en producción."""
    invoice, payment = _invoice_payment(
        db, account, org, plan, pi_id=pi_id, status=PaymentStatus.PENDING.value
    )
    _feed_events(monkeypatch, _succeeded_event(payment, org, plan, event_id=event_id))
    gw_.handle_webhook(db, b"{}", "sig")
    db.refresh(payment)
    db.refresh(invoice)
    sub = db.query(Subscription).filter(Subscription.organization_id == org.id).one()
    return invoice, payment, sub


@pytest.fixture
def gw():
    return StripeGateway()


def test_stripe_config_registers_gateway_on_startup(authenticated_client):
    res = authenticated_client.get("/api/v1/stripe/config")
    assert res.status_code == 200
    body = res.json()
    assert body["gateway"] == "stripe"
    assert "stripe" in body["available_gateways"]


def test_create_payment_intent_reuses_live_pi(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    invoice, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_live",
        status=PaymentStatus.PENDING.value,
    )
    creates = []
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda pi_id: FakePI(
            id=pi_id, status="requires_payment_method", client_secret="cs_reuse"
        ),
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: creates.append(kwargs) or FakePI(id="pi_new"),
    )

    result = gw.create_payment_intent(
        db_session, test_organization_data.id, plan.id, "MONTHLY"
    )
    assert result["client_token"] == "cs_reuse"
    assert result["payment_id"] == str(payment.id)
    assert creates == []


def test_create_payment_intent_rejects_successful_period(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_paid",
        status=PaymentStatus.SUCCESS.value,
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("no debe crear PI")),
    )
    with pytest.raises(HTTPException) as exc:
        gw.create_payment_intent(
            db_session, test_organization_data.id, plan.id, "MONTHLY"
        )
    assert exc.value.status_code == 409


def test_yearly_bucket_blocks_second_charge_in_same_year(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_year",
        status=PaymentStatus.SUCCESS.value,
        cycle="YEARLY",
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("no debe crear PI yearly")
        ),
    )
    with pytest.raises(HTTPException) as exc:
        gw.create_payment_intent(
            db_session, test_organization_data.id, plan.id, "YEARLY"
        )
    assert exc.value.status_code == 409


def test_yearly_legacy_yyyymm_key_still_blocks_second_charge(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_year_legacy",
        status=PaymentStatus.SUCCESS.value,
        cycle="YEARLY",
    )
    legacy = gw._idem_key(
        "pi",
        str(test_account_data.id),
        str(plan.id),
        "YEARLY",
        datetime.now(timezone.utc).strftime("%Y%m"),
    )
    payment.idempotency_key = legacy
    db_session.commit()
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("no debe crear PI yearly legacy")
        ),
    )
    with pytest.raises(HTTPException) as exc:
        gw.create_payment_intent(
            db_session, test_organization_data.id, plan.id, "YEARLY"
        )
    assert exc.value.status_code == 409


def test_create_payment_intent_does_not_preattach_default_card(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    now = datetime.now(timezone.utc)
    db_session.add(
        PaymentMethod(
            id=uuid4(),
            account_id=test_account_data.id,
            gateway=GATEWAY,
            method_type="card",
            external_token="pm_default_qa",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2099,
            extra_data={},
            is_default=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakePI(id="pi_no_pm", metadata=kwargs.get("metadata") or {})

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)
    gw.create_payment_intent(db_session, test_organization_data.id, plan.id, "MONTHLY")
    assert "payment_method" not in captured


def test_setup_intent_uses_a_fresh_stripe_key_per_call(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    _customer(db_session, test_account_data)
    keys = []

    class FakeSI:
        client_secret = "seti_secret"

    def fake_create(**kwargs):
        keys.append(kwargs.get("idempotency_key"))
        return FakeSI()

    monkeypatch.setattr(stripe_mod.SetupIntent, "create", fake_create)
    first = gw.create_setup_intent(db_session, test_organization_data.id)
    second = gw.create_setup_intent(db_session, test_organization_data.id)
    assert first["client_token"] == "seti_secret"
    assert second["client_token"] == "seti_secret"
    assert len(keys) == 2
    assert keys[0] and keys[0] != keys[1]


def test_confirm_setup_intent_persists_card_without_webhook(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    _customer(db_session, test_account_data)

    class FakeSI:
        id = "seti_new_card"
        status = "succeeded"
        customer = "cus_test_123"
        payment_method = "pm_new_card"

        def to_dict(self):
            return {
                "id": self.id,
                "status": self.status,
                "customer": self.customer,
                "payment_method": self.payment_method,
            }

    class FakePM:
        def to_dict(self):
            return {
                "id": "pm_new_card",
                "card": {
                    "brand": "visa",
                    "last4": "4242",
                    "exp_month": 12,
                    "exp_year": 2099,
                    "fingerprint": "fp_new",
                },
            }

    monkeypatch.setattr(stripe_mod.SetupIntent, "retrieve", lambda _sid: FakeSI())
    monkeypatch.setattr(stripe_mod.PaymentMethod, "retrieve", lambda _pmid: FakePM())

    listed = gw.confirm_setup_intent(
        db_session, test_organization_data.id, "seti_new_card"
    )
    assert len(listed) == 1
    assert listed[0]["last4"] == "4242"
    assert listed[0]["is_default"] is True

    again = gw.confirm_setup_intent(
        db_session, test_organization_data.id, "seti_new_card"
    )
    assert len(again) == 1
    assert again[0]["external_token"] == "pm_new_card"


def test_confirm_setup_intent_rejects_foreign_customer(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    _customer(db_session, test_account_data)

    class FakeSI:
        status = "succeeded"
        customer = "cus_other"
        payment_method = "pm_x"

        def to_dict(self):
            return {
                "status": self.status,
                "customer": self.customer,
                "payment_method": self.payment_method,
            }

    monkeypatch.setattr(stripe_mod.SetupIntent, "retrieve", lambda _sid: FakeSI())
    with pytest.raises(HTTPException) as exc:
        gw.confirm_setup_intent(db_session, test_organization_data.id, "seti_foreign")
    assert exc.value.status_code == 403


def test_confirm_setup_intent_rejects_malformed_id(
    db_session, test_organization_data, gw
):
    with pytest.raises(HTTPException) as exc:
        gw.confirm_setup_intent(db_session, test_organization_data.id, "pi_not_setup")
    assert exc.value.status_code == 400


def test_succeeded_pi_fulfills_pending_row_then_conflicts(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    invoice, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_done",
        status=PaymentStatus.PENDING.value,
    )

    def retrieve(pi_id):
        return FakePI(
            id=pi_id,
            status="succeeded",
            metadata={
                "organization_id": str(test_organization_data.id),
                "plan_id": str(plan.id),
                "billing_cycle": "MONTHLY",
            },
        )

    monkeypatch.setattr(stripe_mod.PaymentIntent, "retrieve", retrieve)

    with pytest.raises(HTTPException) as exc:
        gw.create_payment_intent(
            db_session, test_organization_data.id, plan.id, "MONTHLY"
        )
    assert exc.value.status_code == 409
    db_session.refresh(payment)
    db_session.refresh(invoice)
    assert payment.payment_status == PaymentStatus.SUCCESS.value
    assert invoice.invoice_status == InvoiceStatus.PAID.value
    sub = db_session.query(Subscription).one()
    assert sub.plan_id == plan.id
    assert invoice.subscription_id == sub.id


def _active_sub(db, org, plan, *, cycle="MONTHLY", days_left=10):
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_left)
    sub = Subscription(
        plan_id=plan.id,
        organization_id=org.id,
        status="ACTIVE",
        started_at=now - timedelta(days=20),
        expires_at=end,
        billing_cycle=cycle,
        auto_renew=True,
        current_period_start=now - timedelta(days=20),
        current_period_end=end,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub, end


def test_early_renewal_keeps_the_days_already_paid(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Renovar antes de vencer encadena el período; no se descartan días pagados."""
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    sub, current_end = _active_sub(db_session, test_organization_data, plan)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_renew",
        status=PaymentStatus.PENDING.value,
    )

    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(
            _succeeded_event(
                payment, test_organization_data, plan, event_id="evt_renew"
            )
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(sub)
    new_end = billing_period.as_aware(sub.expires_at)
    assert new_end == billing_period.as_aware(current_end) + timedelta(days=30)
    assert billing_period.as_aware(sub.current_period_start) == billing_period.as_aware(
        current_end
    )


def test_plan_change_restarts_the_period_today(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    old_plan = _plan(db_session)
    new_plan = _plan(db_session)
    _customer(db_session, test_account_data)
    sub, current_end = _active_sub(db_session, test_organization_data, old_plan)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        new_plan,
        pi_id="pi_upgrade",
        status=PaymentStatus.PENDING.value,
    )

    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(
            _succeeded_event(
                payment, test_organization_data, new_plan, event_id="evt_upgrade"
            )
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(sub)
    assert sub.plan_id == new_plan.id
    new_end = billing_period.as_aware(sub.expires_at)
    assert new_end < billing_period.as_aware(current_end) + timedelta(days=30)
    assert new_end > datetime.now(timezone.utc) + timedelta(days=29)


def test_create_payment_intent_amount_comes_from_plan_not_caller(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session, monthly="150.50")
    _customer(db_session, test_account_data)
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakePI(id="pi_amt", metadata=kwargs.get("metadata") or {})

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)
    result = gw.create_payment_intent(
        db_session, test_organization_data.id, plan.id, "MONTHLY"
    )
    # 150.50 + 16% IVA = 174.58
    assert captured["amount"] == 17458
    assert result["amount_mxn"] == "150.50"
    assert result["tax_mxn"] == "24.08"
    assert result["amount_with_iva"] == "174.58"
    assert result["amount_cents"] == 17458


def test_charged_amount_matches_invoice_breakdown(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Lo que Stripe cobra, lo que dice la factura y lo que ve el cliente coinciden."""
    plan = _plan(db_session, monthly="1333.33")
    _customer(db_session, test_account_data)
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakePI(id="pi_iva", amount=kwargs["amount"])

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)
    result = gw.create_payment_intent(
        db_session, test_organization_data.id, plan.id, "MONTHLY"
    )

    payment = (
        db_session.query(Payment).filter(Payment.id == UUID(result["payment_id"])).one()
    )
    invoice = db_session.query(Invoice).filter(Invoice.id == payment.invoice_id).one()

    # 1333.33 * 0.16 = 213.3328 → 213.33; total = 1546.66
    assert invoice.subtotal == Decimal("1333.33")
    assert invoice.tax_amount == Decimal("213.33")
    assert invoice.total_amount == Decimal("1546.66")
    assert payment.amount == invoice.total_amount
    assert captured["amount"] == 154666
    assert result["amount_with_iva"] == "1546.66"
    assert result["amount_cents"] == 154666
    assert result["amount_mxn"] == "1333.33"
    assert result["tax_mxn"] == "213.33"


def test_repriced_plan_cancels_old_pi_and_reissues(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Si el precio cambió, no se reusa un PI que cobraría un importe distinto."""
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_old_price",
        status=PaymentStatus.PENDING.value,
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda pi_id: FakePI(id=pi_id, status="requires_payment_method", amount=29900),
    )
    canceled = []
    monkeypatch.setattr(
        stripe_mod.PaymentIntent, "cancel", lambda pi_id: canceled.append(pi_id)
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: FakePI(id="pi_new_price", amount=kwargs["amount"]),
    )

    result = gw.create_payment_intent(
        db_session, test_organization_data.id, plan.id, "MONTHLY"
    )
    db_session.refresh(payment)
    assert canceled == ["pi_old_price"]
    assert payment.gateway_payment_id == "pi_new_price"
    assert result["amount_with_iva"] == str(MONTHLY_TOTAL)


def test_repriced_plan_is_retryable_when_stripe_cannot_be_reached(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Resultado desconocido → 5xx, para que la key se libere y el reintento sirva."""
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_price_unknown",
        status=PaymentStatus.PENDING.value,
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda pi_id: FakePI(id=pi_id, status="requires_payment_method", amount=29900),
    )

    def cancel(_pi_id):
        raise stripe.error.APIConnectionError("network down")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "cancel", cancel)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("no debe crear PI")),
    )

    with pytest.raises(HTTPException) as exc:
        gw.create_payment_intent(
            db_session, test_organization_data.id, plan.id, "MONTHLY"
        )
    assert exc.value.status_code >= 500
    db_session.refresh(payment)
    assert payment.payment_status == PaymentStatus.PENDING.value
    assert payment.gateway_payment_id == "pi_price_unknown"


def test_repriced_plan_reports_already_paid_if_old_pi_was_charged(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_old_paid",
        status=PaymentStatus.PENDING.value,
    )
    states = iter(["requires_payment_method", "succeeded"])
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda pi_id: FakePI(
            id=pi_id,
            status=next(states),
            amount=29900,
            metadata={
                "organization_id": str(test_organization_data.id),
                "plan_id": str(plan.id),
                "billing_cycle": "MONTHLY",
            },
        ),
    )

    def cancel(_pi_id):
        raise stripe.error.InvalidRequestError("cannot cancel succeeded", "intent")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "cancel", cancel)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("no debe crear PI")),
    )

    with pytest.raises(HTTPException) as exc:
        gw.create_payment_intent(
            db_session, test_organization_data.id, plan.id, "MONTHLY"
        )
    assert exc.value.status_code == 409
    db_session.refresh(payment)
    assert payment.payment_status == PaymentStatus.SUCCESS.value


def test_webhook_invalid_signature_is_400(gw, db_session, monkeypatch):
    def boom(*_a, **_k):
        raise stripe.error.SignatureVerificationError("bad", "sig")

    monkeypatch.setattr(stripe_mod.Webhook, "construct_event", boom)
    with pytest.raises(HTTPException) as exc:
        gw.handle_webhook(db_session, b"{}", "t=1,v1=abc")
    assert exc.value.status_code == 400


def test_webhook_success_is_idempotent_and_keeps_card_enum(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    invoice, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_wh",
        status=PaymentStatus.PENDING.value,
    )
    payload = _succeeded_event(payment, test_organization_data, plan, "evt_dup")
    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(payload),
    )

    gw.handle_webhook(db_session, b"ignored", "sig")
    db_session.refresh(payment)
    assert payment.payment_status == PaymentStatus.SUCCESS.value
    assert payment.payment_method_type == "card"
    assert payment.payment_method_meta.get("brand") == "visa"

    gw.handle_webhook(db_session, b"ignored", "sig")
    events = db_session.query(PaymentGatewayEvent).all()
    assert len(events) == 1
    subs = db_session.query(Subscription).all()
    assert len(subs) == 1
    db_session.refresh(invoice)
    assert invoice.subscription_id == subs[0].id


def test_webhook_second_worker_does_not_reprocess(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_race",
        status=PaymentStatus.PENDING.value,
    )
    payload = _succeeded_event(payment, test_organization_data, plan, "evt_race")
    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(payload),
    )
    claimed_first, ok_first = gw._claim_webhook_event(db_session, payload)
    assert ok_first is True
    claimed_first.event_status = GatewayEventStatus.PROCESSED
    db_session.commit()

    rec, claimed = gw._claim_webhook_event(db_session, payload)
    assert claimed is False
    assert rec.external_event_id == "evt_race"


def test_webhook_subscription_failure_returns_5xx_and_marks_failed(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_fail_sub",
        status=PaymentStatus.PENDING.value,
    )
    payload = _succeeded_event(payment, test_organization_data, plan, "evt_fail")
    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(payload),
    )
    monkeypatch.setattr(
        StripeGateway,
        "_activate_subscription",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    with pytest.raises(HTTPException) as exc:
        gw.handle_webhook(db_session, b"ignored", "sig")
    assert exc.value.status_code == 500
    event = db_session.get(PaymentGatewayEvent, (GATEWAY, "evt_fail"))
    assert event is not None
    status = (
        event.event_status.value
        if hasattr(event.event_status, "value")
        else event.event_status
    )
    assert status == "failed"


def test_extract_brand_prefers_latest_charge(gw):
    brand = gw._extract_brand(
        {
            "charges": {"data": []},
            "latest_charge": {
                "payment_method_details": {"card": {"brand": "mastercard"}}
            },
        }
    )
    assert brand == "mastercard"


def test_period_bucket_yearly_uses_year_only(gw):
    when = datetime(2026, 8, 24, tzinfo=timezone.utc)
    assert gw._period_bucket("MONTHLY", when) == "202608"
    assert gw._period_bucket("YEARLY", when) == "2026"


def test_http_idempotency_replays_without_second_stripe_create(
    authenticated_client,
    db_session,
    test_account_data,
    test_organization_data,
    monkeypatch,
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    creates = []

    def fake_create(**kwargs):
        creates.append(kwargs)
        return FakePI(id="pi_http", metadata=kwargs.get("metadata") or {})

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)
    headers = {"Idempotency-Key": "checkout-session-key-aaaa-bbbb"}
    body = {
        "plan_id": str(plan.id),
        "billing_cycle": "MONTHLY",
        "gateway": "stripe",
    }
    first = authenticated_client.post(
        "/api/v1/stripe/payment-intent", json=body, headers=headers
    )
    second = authenticated_client.post(
        "/api/v1/stripe/payment-intent", json=body, headers=headers
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert len(creates) == 1


def test_http_idempotency_rejects_payload_mismatch(
    authenticated_client,
    db_session,
    test_account_data,
    test_organization_data,
    monkeypatch,
):
    plan_a = _plan(db_session)
    plan_b = _plan(db_session)
    _customer(db_session, test_account_data)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: FakePI(id="pi_mis", metadata=kwargs.get("metadata") or {}),
    )
    headers = {"Idempotency-Key": "checkout-session-key-cccc-dddd"}
    first = authenticated_client.post(
        "/api/v1/stripe/payment-intent",
        json={
            "plan_id": str(plan_a.id),
            "billing_cycle": "MONTHLY",
            "gateway": "stripe",
        },
        headers=headers,
    )
    assert first.status_code == 201
    second = authenticated_client.post(
        "/api/v1/stripe/payment-intent",
        json={
            "plan_id": str(plan_b.id),
            "billing_cycle": "MONTHLY",
            "gateway": "stripe",
        },
        headers=headers,
    )
    assert second.status_code == 409
    assert "payload distinto" in second.json()["detail"]


def test_webhook_http_without_signature_is_rejected(client):
    res = client.post(
        "/api/v1/stripe/webhook/stripe",
        content=b'{"type":"test"}',
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 400


def test_claim_skips_fresh_processing_lock(
    db_session, test_account_data, test_organization_data, gw
):
    plan = _plan(db_session)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_lock",
        status=PaymentStatus.PENDING.value,
    )
    payload = _succeeded_event(payment, test_organization_data, plan, "evt_lock")
    rec, claimed = gw._claim_webhook_event(db_session, payload)
    assert claimed is True
    rec2, claimed_again = gw._claim_webhook_event(db_session, payload)
    assert claimed_again is False
    assert rec2.external_event_id == rec.external_event_id


def test_claim_reclaims_stale_processing(
    db_session, test_account_data, test_organization_data, gw
):
    plan = _plan(db_session)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_stale",
        status=PaymentStatus.PENDING.value,
    )
    payload = _succeeded_event(payment, test_organization_data, plan, "evt_stale")
    rec, claimed = gw._claim_webhook_event(db_session, payload)
    assert claimed is True
    rec.processed_at = datetime.now(timezone.utc) - timedelta(seconds=45)
    db_session.commit()

    rec2, reclaimed = gw._claim_webhook_event(db_session, payload)
    assert reclaimed is True
    assert rec2.retry_count == 1
    assert rec2.event_status in (
        GatewayEventStatus.PROCESSING,
        GatewayEventStatus.PROCESSING.value,
    )


def test_claim_recovers_when_insert_loses_unique_race(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_unique_race",
        status=PaymentStatus.PENDING.value,
    )
    payload = _succeeded_event(payment, test_organization_data, plan, "evt_unique_race")
    first, claimed = gw._claim_webhook_event(db_session, payload)
    first.event_status = GatewayEventStatus.PROCESSED
    db_session.commit()
    db_session.expunge(first)

    original_query = db_session.query
    misses = {"n": 0}

    class _Miss:
        def filter(self, *a, **k):
            return self

        def with_for_update(self):
            return self

        def first(self):
            return None

    def query_first_lookup_misses(*args, **kwargs):
        if args and args[0] is PaymentGatewayEvent:
            misses["n"] += 1
            if misses["n"] == 1:
                return _Miss()
        return original_query(*args, **kwargs)

    monkeypatch.setattr(db_session, "query", query_first_lookup_misses)
    rec, claimed_again = gw._claim_webhook_event(db_session, payload)
    assert claimed_again is False
    assert rec.external_event_id == "evt_unique_race"
    status = (
        rec.event_status.value
        if hasattr(rec.event_status, "value")
        else rec.event_status
    )
    assert status == "processed"


def test_failed_webhook_is_retried_and_fulfills(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    invoice, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_retry",
        status=PaymentStatus.PENDING.value,
    )
    payload = _succeeded_event(payment, test_organization_data, plan, "evt_retry")
    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(payload),
    )
    original_activate = StripeGateway._activate_subscription

    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(StripeGateway, "_activate_subscription", boom)
    with pytest.raises(HTTPException) as exc:
        gw.handle_webhook(db_session, b"ignored", "sig")
    assert exc.value.status_code == 500
    monkeypatch.setattr(StripeGateway, "_activate_subscription", original_activate)

    gw.handle_webhook(db_session, b"ignored", "sig")
    db_session.refresh(payment)
    db_session.refresh(invoice)
    assert payment.payment_status == PaymentStatus.SUCCESS.value
    assert invoice.invoice_status == InvoiceStatus.PAID.value
    event = db_session.get(PaymentGatewayEvent, (GATEWAY, "evt_retry"))
    status = (
        event.event_status.value
        if hasattr(event.event_status, "value")
        else event.event_status
    )
    assert status == "processed"
    assert event.retry_count >= 1


def test_unhandled_webhook_is_skipped(db_session, monkeypatch, gw):
    payload = {
        "id": "evt_skip",
        "type": "radar.early_fraud_warning.created",
        "created": 1,
        "livemode": False,
        "data": {"object": {"id": "issfr_1"}},
    }
    monkeypatch.setattr(
        stripe_mod.Webhook,
        "construct_event",
        lambda *_a, **_k: FakeEvent(payload),
    )
    gw.handle_webhook(db_session, b"ignored", "sig")
    event = db_session.get(PaymentGatewayEvent, (GATEWAY, "evt_skip"))
    assert event is not None
    status = (
        event.event_status.value
        if hasattr(event.event_status, "value")
        else event.event_status
    )
    assert status == "skipped"


def test_canceled_pi_is_reissued_with_new_stripe_key(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_canceled",
        status=PaymentStatus.PENDING.value,
    )
    captured = {}

    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda pi_id: FakePI(id=pi_id, status="canceled"),
    )

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakePI(id="pi_reissued", client_secret="cs_reissued")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", fake_create)
    result = gw.create_payment_intent(
        db_session, test_organization_data.id, plan.id, "MONTHLY"
    )
    assert result["client_token"] == "cs_reissued"
    db_session.refresh(payment)
    assert payment.gateway_payment_id == "pi_reissued"
    assert captured["idempotency_key"] != payment.idempotency_key
    assert captured["amount"] == MONTHLY_CENTS


def test_stale_checkout_already_paid_is_fulfilled_not_canceled(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Un checkout viejo que en realidad ya se cobró jamás debe quedar CANCELED."""
    old_plan = _plan(db_session)
    new_plan = _plan(db_session)
    _customer(db_session, test_account_data)
    old_invoice, old_payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        old_plan,
        pi_id="pi_stale_paid",
        status=PaymentStatus.PENDING.value,
    )

    def cancel(_pi_id):
        raise stripe.error.InvalidRequestError("cannot cancel succeeded", "intent")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "cancel", cancel)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "retrieve",
        lambda pi_id: FakePI(
            id=pi_id,
            status="succeeded",
            metadata={
                "organization_id": str(test_organization_data.id),
                "plan_id": str(old_plan.id),
                "billing_cycle": "MONTHLY",
            },
        ),
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: FakePI(id="pi_new_after_stale"),
    )

    gw.create_payment_intent(
        db_session, test_organization_data.id, new_plan.id, "MONTHLY"
    )
    db_session.refresh(old_payment)
    db_session.refresh(old_invoice)
    assert old_payment.payment_status == PaymentStatus.SUCCESS.value
    assert old_invoice.invoice_status == InvoiceStatus.PAID.value
    sub = db_session.query(Subscription).one()
    assert sub.plan_id == old_plan.id


def test_stale_checkout_stays_pending_when_stripe_is_unreachable(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    old_plan = _plan(db_session)
    new_plan = _plan(db_session)
    _customer(db_session, test_account_data)
    old_invoice, old_payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        old_plan,
        pi_id="pi_stale_unknown",
        status=PaymentStatus.PENDING.value,
    )

    def cancel(_pi_id):
        raise stripe.error.APIConnectionError("network down")

    monkeypatch.setattr(stripe_mod.PaymentIntent, "cancel", cancel)
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: FakePI(id="pi_new_unknown"),
    )

    gw.create_payment_intent(
        db_session, test_organization_data.id, new_plan.id, "MONTHLY"
    )
    db_session.refresh(old_payment)
    db_session.refresh(old_invoice)
    assert old_payment.payment_status == PaymentStatus.PENDING.value
    assert old_invoice.invoice_status == InvoiceStatus.OPEN.value


def test_stale_checkout_is_canceled_and_invoice_voided(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    old_plan = _plan(db_session)
    new_plan = _plan(db_session)
    _customer(db_session, test_account_data)
    old_invoice, old_payment = _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        old_plan,
        pi_id="pi_stale_ok",
        status=PaymentStatus.PENDING.value,
    )
    canceled = []
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "cancel",
        lambda pi_id: canceled.append(pi_id),
    )
    monkeypatch.setattr(
        stripe_mod.PaymentIntent,
        "create",
        lambda **kwargs: FakePI(id="pi_new_ok"),
    )

    gw.create_payment_intent(
        db_session, test_organization_data.id, new_plan.id, "MONTHLY"
    )
    db_session.refresh(old_payment)
    db_session.refresh(old_invoice)
    assert canceled == ["pi_stale_ok"]
    assert old_payment.payment_status == PaymentStatus.CANCELED.value
    assert old_payment.canceled_at is not None
    assert old_invoice.invoice_status == InvoiceStatus.VOID.value
    assert db_session.query(Subscription).count() == 0


def test_full_refund_voids_invoice_and_takes_back_the_period(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    invoice, payment, sub = _paid_subscription(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        gw,
        monkeypatch,
        pi_id="pi_refund_full",
        event_id="evt_paid_full",
    )
    original_end = billing_period.as_aware(sub.expires_at)

    _feed_events(
        monkeypatch,
        _charge_event(
            payment,
            event_id="evt_refund_full",
            amount_refunded=MONTHLY_CENTS,
            refunded=True,
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(payment)
    db_session.refresh(invoice)
    db_session.refresh(sub)
    assert payment.payment_status == PaymentStatus.REFUNDED.value
    assert payment.refunded_amount == MONTHLY_TOTAL
    assert payment.refunded_at is not None
    assert invoice.invoice_status == InvoiceStatus.VOID.value
    assert invoice.paid_at is None
    assert billing_period.as_aware(sub.expires_at) == original_end - timedelta(days=30)
    assert sub.status == SubscriptionStatus.CANCELLED.value
    assert sub.cancelled_at is not None


def test_partial_refund_keeps_the_service_running(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    invoice, payment, sub = _paid_subscription(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        gw,
        monkeypatch,
        pi_id="pi_refund_part",
        event_id="evt_paid_part",
    )
    original_end = billing_period.as_aware(sub.expires_at)

    _feed_events(
        monkeypatch,
        _charge_event(
            payment, event_id="evt_refund_part", amount_refunded=5000, refunded=False
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(payment)
    db_session.refresh(invoice)
    db_session.refresh(sub)
    assert payment.payment_status == PaymentStatus.PARTIALLY_REFUNDED.value
    assert payment.refunded_amount == Decimal("50.00")
    assert invoice.invoice_status == InvoiceStatus.PAID.value
    assert billing_period.as_aware(sub.expires_at) == original_end
    assert sub.status == SubscriptionStatus.ACTIVE.value


def test_repeated_refund_events_take_the_period_only_once(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    """Stripe manda el acumulado devuelto: reprocesar no debe restar dos veces."""
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment, sub = _paid_subscription(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        gw,
        monkeypatch,
        pi_id="pi_refund_twice",
        event_id="evt_paid_twice",
    )
    original_end = billing_period.as_aware(sub.expires_at)

    _feed_events(
        monkeypatch,
        _charge_event(
            payment, event_id="evt_ref_a", amount_refunded=MONTHLY_CENTS, refunded=True
        ),
        _charge_event(
            payment, event_id="evt_ref_b", amount_refunded=MONTHLY_CENTS, refunded=True
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(payment)
    db_session.refresh(sub)
    assert payment.refunded_amount == MONTHLY_TOTAL
    assert billing_period.as_aware(sub.expires_at) == original_end - timedelta(days=30)


def test_refund_never_exceeds_the_amount_charged(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment, _ = _paid_subscription(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        gw,
        monkeypatch,
        pi_id="pi_refund_over",
        event_id="evt_paid_over",
    )
    _feed_events(
        monkeypatch,
        _charge_event(
            payment,
            event_id="evt_ref_over",
            amount_refunded=MONTHLY_CENTS * 3,
            refunded=True,
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(payment)
    assert payment.refunded_amount == MONTHLY_TOTAL


def test_open_dispute_is_flagged_but_service_continues(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _, payment, sub = _paid_subscription(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        gw,
        monkeypatch,
        pi_id="pi_disputed",
        event_id="evt_paid_disp",
    )
    original_end = billing_period.as_aware(sub.expires_at)

    _feed_events(
        monkeypatch,
        _dispute_event(
            payment,
            event_id="evt_disp_open",
            event_type="charge.dispute.created",
            status="needs_response",
            due_by=1893456000,
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(payment)
    db_session.refresh(sub)
    assert payment.is_disputed is True
    assert payment.payment_status == PaymentStatus.DISPUTED.value
    assert payment.dispute_id == "dp_1"
    assert payment.dispute_reason == "fraudulent"
    assert payment.dispute_due_at is not None
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert billing_period.as_aware(sub.expires_at) == original_end


def test_lost_dispute_marks_uncollectible_and_revokes_the_period(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    invoice, payment, sub = _paid_subscription(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        gw,
        monkeypatch,
        pi_id="pi_disp_lost",
        event_id="evt_paid_lost",
    )
    original_end = billing_period.as_aware(sub.expires_at)

    _feed_events(
        monkeypatch,
        _dispute_event(
            payment,
            event_id="evt_disp_open2",
            event_type="charge.dispute.created",
            status="needs_response",
        ),
        _dispute_event(
            payment,
            event_id="evt_disp_lost",
            event_type="charge.dispute.closed",
            status="lost",
        ),
    )
    gw.handle_webhook(db_session, b"{}", "sig")
    gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(payment)
    db_session.refresh(invoice)
    db_session.refresh(sub)
    assert payment.dispute_status == "lost"
    assert payment.dispute_resolved_at is not None
    assert invoice.invoice_status == InvoiceStatus.UNCOLLECTIBLE.value
    assert billing_period.as_aware(sub.expires_at) == original_end - timedelta(days=30)
    assert sub.status == SubscriptionStatus.CANCELLED.value


def test_won_dispute_restores_the_payment_and_the_period(
    db_session, test_account_data, test_organization_data, monkeypatch, gw
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    invoice, payment, sub = _paid_subscription(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        gw,
        monkeypatch,
        pi_id="pi_disp_won",
        event_id="evt_paid_won",
    )
    original_end = billing_period.as_aware(sub.expires_at)

    _feed_events(
        monkeypatch,
        _dispute_event(
            payment,
            event_id="evt_disp_open3",
            event_type="charge.dispute.created",
            status="needs_response",
        ),
        _dispute_event(
            payment,
            event_id="evt_disp_lost3",
            event_type="charge.dispute.closed",
            status="lost",
        ),
        _dispute_event(
            payment,
            event_id="evt_disp_won3",
            event_type="charge.dispute.closed",
            status="won",
        ),
    )
    for _ in range(3):
        gw.handle_webhook(db_session, b"{}", "sig")

    db_session.refresh(payment)
    db_session.refresh(invoice)
    db_session.refresh(sub)
    assert payment.is_disputed is False
    assert payment.payment_status == PaymentStatus.SUCCESS.value
    assert invoice.invoice_status == InvoiceStatus.PAID.value
    assert invoice.paid_at is not None
    assert billing_period.as_aware(sub.expires_at) == original_end
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.cancelled_at is None


def test_refund_without_local_payment_is_acknowledged_not_retried(
    db_session, monkeypatch, gw
):
    """Sin fila local no hay nada que ajustar; se registra y se responde 200."""
    _feed_events(
        monkeypatch,
        {
            "id": "evt_orphan_refund",
            "type": "charge.refunded",
            "created": 1,
            "livemode": False,
            "data": {
                "object": {
                    "id": "ch_orphan",
                    "payment_intent": "pi_desconocido",
                    "amount": 1000,
                    "amount_refunded": 1000,
                    "refunded": True,
                }
            },
        },
    )
    gw.handle_webhook(db_session, b"{}", "sig")
    rec = (
        db_session.query(PaymentGatewayEvent)
        .filter(PaymentGatewayEvent.external_event_id == "evt_orphan_refund")
        .one()
    )
    assert rec.event_status in (GatewayEventStatus.PROCESSED, "processed")


def test_zero_price_plan_is_rejected(
    db_session, test_account_data, test_organization_data, gw
):
    plan = _plan(db_session, monthly="0.00")
    _customer(db_session, test_account_data)
    with pytest.raises(HTTPException) as exc:
        gw.create_payment_intent(
            db_session, test_organization_data.id, plan.id, "MONTHLY"
        )
    assert exc.value.status_code == 400


def test_http_invalid_idempotency_key_is_400(
    authenticated_client, db_session, test_account_data, test_organization_data
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    res = authenticated_client.post(
        "/api/v1/stripe/payment-intent",
        json={
            "plan_id": str(plan.id),
            "billing_cycle": "MONTHLY",
            "gateway": "stripe",
        },
        headers={"Idempotency-Key": "bad@key"},
    )
    assert res.status_code == 400
    assert "Idempotency-Key" in res.json()["detail"]


def test_http_missing_idempotency_key_is_400(
    authenticated_client, db_session, test_account_data, test_organization_data
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    res = authenticated_client.post(
        "/api/v1/stripe/payment-intent",
        json={
            "plan_id": str(plan.id),
            "billing_cycle": "MONTHLY",
            "gateway": "stripe",
        },
    )
    assert res.status_code == 400
    assert "obligatoria" in res.json()["detail"]


def test_http_5xx_abandons_key_so_retry_can_charge(
    authenticated_client,
    db_session,
    test_account_data,
    test_organization_data,
    monkeypatch,
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    creates = []

    def flaky_create(**kwargs):
        if not creates:
            creates.append("fail")
            raise stripe.error.APIConnectionError("network down")
        creates.append(kwargs)
        return FakePI(id="pi_after_retry", metadata=kwargs.get("metadata") or {})

    monkeypatch.setattr(stripe_mod.PaymentIntent, "create", flaky_create)
    headers = {"Idempotency-Key": "checkout-session-key-eeee-ffff"}
    body = {
        "plan_id": str(plan.id),
        "billing_cycle": "MONTHLY",
        "gateway": "stripe",
    }
    first = authenticated_client.post(
        "/api/v1/stripe/payment-intent", json=body, headers=headers
    )
    assert first.status_code == 502
    leftover = (
        db_session.query(ApiIdempotencyRequest)
        .filter(ApiIdempotencyRequest.idempotency_key == headers["Idempotency-Key"])
        .all()
    )
    assert leftover == []

    second = authenticated_client.post(
        "/api/v1/stripe/payment-intent", json=body, headers=headers
    )
    assert second.status_code == 201
    assert second.json()["payment_id"]
    assert sum(1 for c in creates if c != "fail") == 1


def test_http_replays_cached_already_processed_conflict(
    authenticated_client,
    db_session,
    test_account_data,
    test_organization_data,
    monkeypatch,
):
    plan = _plan(db_session)
    _customer(db_session, test_account_data)
    _invoice_payment(
        db_session,
        test_account_data,
        test_organization_data,
        plan,
        pi_id="pi_cached_409",
        status=PaymentStatus.SUCCESS.value,
    )
    calls = {"n": 0}
    original = StripeGateway.create_payment_intent

    def counted(self, *args, **kwargs):
        calls["n"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(StripeGateway, "create_payment_intent", counted)
    headers = {"Idempotency-Key": "checkout-session-key-gggg-hhhh"}
    body = {
        "plan_id": str(plan.id),
        "billing_cycle": "MONTHLY",
        "gateway": "stripe",
    }
    first = authenticated_client.post(
        "/api/v1/stripe/payment-intent", json=body, headers=headers
    )
    second = authenticated_client.post(
        "/api/v1/stripe/payment-intent", json=body, headers=headers
    )
    assert first.status_code == 409
    assert second.status_code == 409
    assert first.json()["detail"] == second.json()["detail"]
    assert "procesado" in first.json()["detail"]
    assert calls["n"] == 1


def test_payment_intent_rejects_client_supplied_amount():
    """Un cliente no puede meter el monto en el body: extra=forbid."""
    from uuid import uuid4

    from pydantic import ValidationError

    from app.api.v1.endpoints.stripe_billing import PaymentIntentRequest

    with pytest.raises(ValidationError):
        PaymentIntentRequest(
            plan_id=uuid4(),
            billing_cycle="MONTHLY",
            amount=1,
        )


def test_quote_endpoint_returns_official_breakdown(
    authenticated_client, db_session, test_organization_data
):
    plan = _plan(db_session, monthly="1333.33")
    res = authenticated_client.get(
        "/api/v1/stripe/quote",
        params={"plan_id": str(plan.id), "billing_cycle": "MONTHLY"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["subtotal"] == "1333.33"
    assert body["tax"] == "213.33"
    assert body["total"] == "1546.66"
    assert body["amount_cents"] == 154666
    assert isinstance(body["total"], str)
    assert isinstance(body["amount_cents"], int)
