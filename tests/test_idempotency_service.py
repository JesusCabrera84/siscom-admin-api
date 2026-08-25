"""Tests de la reserva HTTP de idempotencia (cliente → API)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.idempotency import (
    IDEMPOTENCY_COMPLETED,
    IDEMPOTENCY_IN_PROGRESS,
    ApiIdempotencyRequest,
)
from app.services.idempotency_service import (
    PAYMENT_INTENT_ENDPOINT,
    abandon_idempotency,
    begin_idempotency,
    canonical_request_hash,
    complete_idempotency,
    require_idempotency_key,
    validate_idempotency_key,
)


def test_validate_idempotency_key_rejects_pii_and_short_values():
    with pytest.raises(HTTPException) as exc:
        validate_idempotency_key("a@b.com")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException):
        validate_idempotency_key("short")

    with pytest.raises(HTTPException):
        validate_idempotency_key("")


def test_require_idempotency_key_rejects_missing_or_blank():
    with pytest.raises(HTTPException) as exc:
        require_idempotency_key(None)
    assert exc.value.status_code == 400
    assert "obligatoria" in str(exc.value.detail)

    with pytest.raises(HTTPException) as exc:
        require_idempotency_key("   ")
    assert exc.value.status_code == 400
    assert "obligatoria" in str(exc.value.detail)


def test_canonical_hash_is_stable_regardless_of_key_order():
    a = canonical_request_hash({"plan_id": "1", "billing_cycle": "MONTHLY"})
    b = canonical_request_hash({"billing_cycle": "MONTHLY", "plan_id": "1"})
    c = canonical_request_hash({"plan_id": "1", "billing_cycle": "YEARLY"})
    assert a == b
    assert a != c


def test_begin_replays_completed_response(db_session, test_account_data):
    idem_header = "idem-key-replay-ok-12345"
    digest = canonical_request_hash({"plan_id": "p1"})
    first = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    assert first.cached is None
    complete_idempotency(db_session, first, 201, {"client_token": "cs_1"})

    second = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    assert second.cached is not None
    assert second.cached.status_code == 201
    assert second.cached.body["client_token"] == "cs_1"


def test_begin_rejects_same_key_with_different_payload(db_session, test_account_data):
    idem_header = "idem-key-mismatch-12345"
    begin_idempotency(
        db_session,
        idem_header,
        test_account_data.id,
        PAYMENT_INTENT_ENDPOINT,
        canonical_request_hash({"plan_id": "p1"}),
    )
    rec = db_session.query(ApiIdempotencyRequest).one()
    rec.status = IDEMPOTENCY_COMPLETED
    rec.status_code = 201
    rec.response_body = {"ok": True}
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        begin_idempotency(
            db_session,
            idem_header,
            test_account_data.id,
            PAYMENT_INTENT_ENDPOINT,
            canonical_request_hash({"plan_id": "p2"}),
        )
    assert exc.value.status_code == 409
    assert "payload distinto" in str(exc.value.detail)


def test_in_progress_is_rejected_until_stale(db_session, test_account_data):
    idem_header = "idem-key-in-progress-123"
    digest = canonical_request_hash({"plan_id": "p1"})
    begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )

    with pytest.raises(HTTPException) as exc:
        begin_idempotency(
            db_session,
            idem_header,
            test_account_data.id,
            PAYMENT_INTENT_ENDPOINT,
            digest,
        )
    assert exc.value.status_code == 409
    assert "en proceso" in str(exc.value.detail)


def test_stale_in_progress_is_taken_over(db_session, test_account_data):
    idem_header = "idem-key-stale-takeover-1"
    digest = canonical_request_hash({"plan_id": "p1"})
    first = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    rec = db_session.get(ApiIdempotencyRequest, first.record_id)
    rec.created_at = datetime.now(timezone.utc) - timedelta(seconds=45)
    db_session.commit()

    second = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    assert second.cached is None
    assert second.record_id == first.record_id


def test_expired_key_can_be_reused_with_new_payload(db_session, test_account_data):
    idem_header = "idem-key-expired-reuse-12"
    first = begin_idempotency(
        db_session,
        idem_header,
        test_account_data.id,
        PAYMENT_INTENT_ENDPOINT,
        canonical_request_hash({"plan_id": "p1"}),
    )
    complete_idempotency(db_session, first, 201, {"client_token": "cs_old"})
    rec = db_session.get(ApiIdempotencyRequest, first.record_id)
    rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    second = begin_idempotency(
        db_session,
        idem_header,
        test_account_data.id,
        PAYMENT_INTENT_ENDPOINT,
        canonical_request_hash({"plan_id": "p2"}),
    )
    assert second.cached is None
    assert second.record_id == first.record_id
    rec = db_session.get(ApiIdempotencyRequest, second.record_id)
    assert rec.status == IDEMPOTENCY_IN_PROGRESS
    assert rec.request_hash == canonical_request_hash({"plan_id": "p2"})


def test_abandon_allows_retry_after_unknown_failure(db_session, test_account_data):
    idem_header = "idem-key-abandon-retry-1"
    digest = canonical_request_hash({"plan_id": "p1"})
    first = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    abandon_idempotency(db_session, first)

    retry = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    assert retry.cached is None
    leftover = (
        db_session.query(ApiIdempotencyRequest)
        .filter(ApiIdempotencyRequest.status == IDEMPOTENCY_IN_PROGRESS)
        .count()
    )
    assert leftover == 1


def test_abandon_after_failed_flush(
    db_session, test_account_data, test_organization_data
):
    """Un flush fallido deja la sesión en rollback; abandonar no debe explotar."""
    from decimal import Decimal
    from uuid import uuid4

    from app.models.invoice import Invoice, InvoiceStatus

    idem_header = "idem-key-abandon-after-flush-1"
    digest = canonical_request_hash({"plan_id": "p1"})
    first = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    shared = f"INV-TEST-{uuid4().hex[:8]}"
    db_session.add(
        Invoice(
            account_id=test_account_data.id,
            organization_id=test_organization_data.id,
            invoice_number=shared,
            invoice_status=InvoiceStatus.OPEN.value,
            subtotal=Decimal("10"),
            total_amount=Decimal("10"),
        )
    )
    db_session.flush()
    db_session.add(
        Invoice(
            account_id=test_account_data.id,
            organization_id=test_organization_data.id,
            invoice_number=shared,
            invoice_status=InvoiceStatus.OPEN.value,
            subtotal=Decimal("10"),
            total_amount=Decimal("10"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()

    abandon_idempotency(db_session, first)

    retry = begin_idempotency(
        db_session, idem_header, test_account_data.id, PAYMENT_INTENT_ENDPOINT, digest
    )
    assert retry.cached is None
