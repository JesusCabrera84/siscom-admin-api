"""Comprobante de pago en PDF. No es un CFDI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fpdf import FPDF
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.organization import Organization
from app.models.payment import Payment, PaymentStatus
from app.models.plan import Plan
from app.services import money

_MX_TZ = ZoneInfo("America/Mexico_City")
_SAFE_FOLIO = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class ReceiptData:
    invoice_number: str
    organization_name: str
    description: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    currency: str
    paid_at: datetime | None
    card_brand: str | None
    card_last4: str | None


def invoice_allows_receipt(invoice: Invoice, payment: Payment | None) -> bool:
    if invoice.invoice_status == InvoiceStatus.PAID.value or invoice.paid_at:
        return True
    return bool(
        payment is not None and payment.payment_status == PaymentStatus.SUCCESS.value
    )


def receipt_filename(invoice_number: str) -> str:
    folio = _SAFE_FOLIO.sub("-", invoice_number or "pago").strip("-") or "pago"
    return f"comprobante-{folio}.pdf"


def load_receipt_data(
    db: Session, invoice: Invoice
) -> tuple[ReceiptData, Payment | None]:
    payment = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice.id)
        .order_by(Payment.succeeded_at.desc().nullslast(), Payment.created_at.desc())
        .first()
    )
    org = (
        db.query(Organization)
        .filter(Organization.id == invoice.organization_id)
        .first()
    )
    description = "Suscripción NEXUS"
    extra = payment.extra_data if payment else {}
    plan_id = extra.get("plan_id") if extra else None
    if plan_id:
        try:
            plan = db.query(Plan).filter(Plan.id == UUID(str(plan_id))).first()
        except (TypeError, ValueError):
            plan = None
        if plan and plan.name:
            cycle = (extra.get("billing_cycle") or "").upper()
            period = "anual" if cycle == "YEARLY" else "mensual"
            description = f"{plan.name} · {period}"

    meta = (payment.payment_method_meta or {}) if payment else {}
    return (
        ReceiptData(
            invoice_number=invoice.invoice_number,
            organization_name=org.name if org else "Cuenta NEXUS",
            description=description,
            subtotal=money.parse(invoice.subtotal or 0),
            tax=money.parse(invoice.tax_amount or 0),
            total=money.parse(invoice.total_amount or 0),
            currency=(invoice.currency or "MXN").upper(),
            paid_at=invoice.paid_at or (payment.succeeded_at if payment else None),
            card_brand=meta.get("brand"),
            card_last4=meta.get("last4"),
        ),
        payment,
    )


def render_receipt_pdf(data: ReceiptData) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.compress = False
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, text="GEMINIS LABS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, text="NEXUS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, text="Comprobante de pago", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(
        0,
        5,
        text=(
            "Este documento acredita el cobro de la suscripcion. "
            "No es un CFDI ni una factura fiscal del SAT."
        ),
    )
    pdf.ln(6)

    pdf.set_draw_color(226, 232, 240)
    y = pdf.get_y()
    pdf.line(18, y, 198, y)
    pdf.ln(6)

    _kv(pdf, "Folio", data.invoice_number)
    _kv(pdf, "Cuenta", data.organization_name)
    _kv(pdf, "Concepto", data.description)
    _kv(pdf, "Fecha de pago", _fmt_dt(data.paid_at))
    _kv(pdf, "Metodo", _fmt_card(data.card_brand, data.card_last4))

    pdf.ln(4)
    y = pdf.get_y()
    pdf.line(18, y, 198, y)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, text="IMPORTE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    _amount_row(pdf, "Subtotal", data.subtotal, data.currency, bold=False)
    _amount_row(pdf, "IVA (16%)", data.tax, data.currency, bold=False)
    pdf.ln(1)
    y = pdf.get_y()
    pdf.set_draw_color(15, 23, 42)
    pdf.line(18, y, 198, y)
    pdf.ln(3)
    _amount_row(pdf, "Total pagado", data.total, data.currency, bold=True)

    pdf.set_y(250)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(
        0,
        4,
        text=(
            "Geminis Labs. Conserva este comprobante con tu historial de pagos. "
            "Si necesitas factura fiscal, pidela por el canal de facturacion."
        ),
    )
    return bytes(pdf.output())


def _kv(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(42, 6, text=label.upper())
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, text=value, new_x="LMARGIN", new_y="NEXT")


def _amount_row(
    pdf: FPDF, label: str, amount: Decimal, currency: str, *, bold: bool
) -> None:
    pdf.set_font("Helvetica", "B" if bold else "", 11 if bold else 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(120, 8, text=label)
    pdf.cell(
        0, 8, text=_mxn(amount, currency), align="R", new_x="LMARGIN", new_y="NEXT"
    )


def _mxn(amount: Decimal, currency: str) -> str:
    return f"$ {money.dump(amount)} {currency}"


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "Pendiente de acreditacion"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(_MX_TZ)
    return local.strftime("%d/%m/%Y %H:%M") + " (Ciudad de Mexico)"


def _fmt_card(brand: str | None, last4: str | None) -> str:
    label = (brand or "Tarjeta").strip().title()
    if last4:
        return f"{label}  **** {last4}"
    return label
