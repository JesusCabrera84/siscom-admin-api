"""Comprobante de pago en PDF."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.services.receipt_pdf import (
    ReceiptData,
    invoice_allows_receipt,
    receipt_filename,
    render_receipt_pdf,
)


def test_receipt_pdf_contains_folio_and_totals():
    pdf = render_receipt_pdf(
        ReceiptData(
            invoice_number="INV-2026-0002",
            organization_name="Org Demo",
            description="NEXUS Core · mensual",
            subtotal=Decimal("230.00"),
            tax=Decimal("36.80"),
            total=Decimal("266.80"),
            currency="MXN",
            paid_at=datetime(2026, 8, 24, 23, 0, tzinfo=timezone.utc),
            card_brand="visa",
            card_last4="4242",
        )
    )
    assert pdf.startswith(b"%PDF")
    assert b"INV-2026-0002" in pdf
    assert b"266.80" in pdf
    assert b"CFDI" in pdf
    assert b"4242" in pdf
    assert b"pi_" not in pdf
    assert b"REFERENCIA" not in pdf


def test_receipt_filename_strips_unsafe_chars():
    assert receipt_filename("INV-2026-0001") == "comprobante-INV-2026-0001.pdf"
    assert receipt_filename("INV 2026/0001") == "comprobante-INV-2026-0001.pdf"


def test_open_invoice_without_success_has_no_receipt():
    invoice = Invoice(
        invoice_number="INV-2026-0003",
        invoice_status=InvoiceStatus.OPEN.value,
        subtotal=Decimal("10"),
        total_amount=Decimal("10"),
    )
    assert invoice_allows_receipt(invoice, None) is False


def test_download_receipt_pdf_for_paid_invoice(
    authenticated_client, db_session, test_account_data, test_organization_data
):
    invoice = Invoice(
        account_id=test_account_data.id,
        organization_id=test_organization_data.id,
        invoice_number="INV-2026-0099",
        invoice_status=InvoiceStatus.PAID.value,
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("16.00"),
        total_amount=Decimal("116.00"),
        currency="MXN",
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add(
        Payment(
            invoice_id=invoice.id,
            account_id=test_account_data.id,
            organization_id=test_organization_data.id,
            gateway="stripe",
            gateway_payment_id="pi_receipt_ok",
            payment_method_type="card",
            payment_method_meta={"brand": "visa", "last4": "4242"},
            amount=Decimal("116.00"),
            currency="MXN",
            payment_status=PaymentStatus.SUCCESS.value,
            extra_data={},
        )
    )
    db_session.commit()

    listed = authenticated_client.get("/api/v1/billing/invoices")
    assert listed.status_code == 200
    row = next(i for i in listed.json()["invoices"] if i["id"] == str(invoice.id))
    assert row["has_receipt"] is True

    res = authenticated_client.get(f"/api/v1/billing/invoices/{invoice.id}/receipt.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/pdf")
    assert "comprobante-INV-2026-0099.pdf" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF")
    assert b"INV-2026-0099" in res.content


def test_download_receipt_pdf_rejected_if_unpaid(
    authenticated_client, db_session, test_account_data, test_organization_data
):
    invoice = Invoice(
        id=uuid4(),
        account_id=test_account_data.id,
        organization_id=test_organization_data.id,
        invoice_number="INV-2026-0100",
        invoice_status=InvoiceStatus.OPEN.value,
        subtotal=Decimal("100.00"),
        total_amount=Decimal("116.00"),
        currency="MXN",
    )
    db_session.add(invoice)
    db_session.commit()

    res = authenticated_client.get(f"/api/v1/billing/invoices/{invoice.id}/receipt.pdf")
    assert res.status_code == 409
    assert "acredite" in res.json()["detail"]
