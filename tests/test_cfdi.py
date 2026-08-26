"""Perfil fiscal y timbrado CFDI (Facturapi mockeado, sin red)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus

TEST_RFC = "ABC101010111"
TEST_PROFILE = {
    "rfc": TEST_RFC,
    "legal_name": "Dunder Mifflin",
    "tax_system": "601",
    "zip": "85900",
    "email": "facturacion@example.com",
    "default_cfdi_use": "G03",
}


def _mock_facturapi():
    client = MagicMock()
    client.livemode = False
    client.create_or_update_customer.return_value = {"id": "cus_test_1"}
    client.create_invoice.return_value = {
        "id": "in_facturapi_1",
        "uuid": "39c85a3f-275b-4341-b259-e8971d9f8a94",
        "status": "valid",
    }
    client.get_invoice_file.return_value = b"%PDF-cfdi"
    return client


def test_get_tax_profile_empty_form(
    authenticated_client,
):
    res = authenticated_client.get("/api/v1/billing/tax-profile")
    assert res.status_code == 200
    body = res.json()
    assert body["is_complete"] is False
    assert body["rfc"] is None
    assert body["default_cfdi_use"] == "G03"
    assert any(item["code"] == "601" for item in body["tax_systems"])
    assert any(item["code"] == "G03" for item in body["cfdi_uses"])


def test_put_tax_profile_syncs_customer(authenticated_client):
    fake = _mock_facturapi()
    with patch("app.services.cfdi_service.FacturapiClient", return_value=fake):
        res = authenticated_client.put("/api/v1/billing/tax-profile", json=TEST_PROFILE)
    assert res.status_code == 200
    body = res.json()
    assert body["is_complete"] is True
    assert body["rfc"] == TEST_RFC
    assert body["zip"] == "85900"
    fake.create_or_update_customer.assert_called_once()
    payload = fake.create_or_update_customer.call_args.args[0]
    assert payload["tax_id"] == TEST_RFC
    assert payload["tax_system"] == "601"
    assert payload["address"]["zip"] == "85900"


def test_put_tax_profile_rejects_invalid_rfc(authenticated_client):
    fake = _mock_facturapi()
    with patch("app.services.cfdi_service.FacturapiClient", return_value=fake):
        res = authenticated_client.put(
            "/api/v1/billing/tax-profile",
            json={**TEST_PROFILE, "rfc": "NO-ES-RFC"},
        )
    assert res.status_code == 400
    assert "RFC" in res.json()["detail"]
    fake.create_or_update_customer.assert_not_called()


def test_stamp_cfdi_rejected_if_unpaid(
    authenticated_client, db_session, test_account_data, test_organization_data
):
    fake = _mock_facturapi()
    with patch("app.services.cfdi_service.FacturapiClient", return_value=fake):
        authenticated_client.put("/api/v1/billing/tax-profile", json=TEST_PROFILE)
        invoice = Invoice(
            account_id=test_account_data.id,
            organization_id=test_organization_data.id,
            invoice_number="INV-2026-CFDI-OPEN",
            invoice_status=InvoiceStatus.OPEN.value,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("16.00"),
            total_amount=Decimal("116.00"),
            currency="MXN",
        )
        db_session.add(invoice)
        db_session.commit()
        res = authenticated_client.post(
            f"/api/v1/billing/invoices/{invoice.id}/cfdi",
            json={"use": "G03"},
        )
    assert res.status_code == 409
    assert "acreditado" in res.json()["detail"]
    fake.create_invoice.assert_not_called()


def test_stamp_cfdi_once_and_download(
    authenticated_client, db_session, test_account_data, test_organization_data
):
    fake = _mock_facturapi()
    with patch("app.services.cfdi_service.FacturapiClient", return_value=fake):
        profile_res = authenticated_client.put(
            "/api/v1/billing/tax-profile", json=TEST_PROFILE
        )
        assert profile_res.status_code == 200

        invoice = Invoice(
            account_id=test_account_data.id,
            organization_id=test_organization_data.id,
            invoice_number="INV-2026-CFDI-0001",
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
                gateway_payment_id="pi_cfdi_ok",
                payment_method_type="card",
                amount=Decimal("116.00"),
                currency="MXN",
                payment_status=PaymentStatus.SUCCESS.value,
                extra_data={},
            )
        )
        db_session.commit()

        first = authenticated_client.post(
            f"/api/v1/billing/invoices/{invoice.id}/cfdi",
            json={"use": "G03"},
        )
        assert first.status_code == 200
        body = first.json()
        assert body["has_cfdi"] is True
        assert body["cfdi_uuid"] == "39c85a3f-275b-4341-b259-e8971d9f8a94"

        listed = authenticated_client.get("/api/v1/billing/invoices")
        row = next(i for i in listed.json()["invoices"] if i["id"] == str(invoice.id))
        assert row["has_cfdi"] is True
        assert row["has_receipt"] is True

        second = authenticated_client.post(
            f"/api/v1/billing/invoices/{invoice.id}/cfdi",
            json={"use": "G03"},
        )
        assert second.status_code == 200
        assert second.json()["cfdi_uuid"] == body["cfdi_uuid"]
        assert fake.create_invoice.call_count == 1
        payload = fake.create_invoice.call_args.args[0]
        assert payload["payment_method"] == "PUE"
        assert payload["payment_form"] == "04"
        assert payload["idempotency_key"] == str(invoice.id)
        assert payload["items"][0]["product"]["tax_included"] is True
        assert payload["items"][0]["product"]["price"] == 116.0
        assert payload["pdf_options"] == {"round_unit_price": True}

        pdf = authenticated_client.get(
            f"/api/v1/billing/invoices/{invoice.id}/cfdi.pdf"
        )
        assert pdf.status_code == 200
        assert pdf.content == b"%PDF-cfdi"
        assert "cfdi-INV-2026-CFDI-0001.pdf" in pdf.headers["content-disposition"]
        fake.get_invoice_file.assert_called_with("in_facturapi_1", "pdf")

        fake.get_invoice_file.return_value = b"<cfdi/>"
        xml = authenticated_client.get(
            f"/api/v1/billing/invoices/{invoice.id}/cfdi.xml"
        )
        assert xml.status_code == 200
        assert xml.content == b"<cfdi/>"


def test_stamp_cfdi_requires_tax_profile(
    authenticated_client, db_session, test_account_data, test_organization_data
):
    invoice = Invoice(
        id=uuid4(),
        account_id=test_account_data.id,
        organization_id=test_organization_data.id,
        invoice_number="INV-2026-CFDI-NOPROFILE",
        invoice_status=InvoiceStatus.PAID.value,
        subtotal=Decimal("100.00"),
        total_amount=Decimal("116.00"),
        currency="MXN",
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(invoice)
    db_session.commit()
    fake = _mock_facturapi()
    with patch("app.services.cfdi_service.FacturapiClient", return_value=fake):
        res = authenticated_client.post(
            f"/api/v1/billing/invoices/{invoice.id}/cfdi", json={}
        )
    assert res.status_code == 409
    assert "datos fiscales" in res.json()["detail"]
    fake.create_invoice.assert_not_called()
