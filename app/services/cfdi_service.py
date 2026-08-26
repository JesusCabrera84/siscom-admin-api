"""Perfil fiscal y timbrado CFDI 4.0 vía Facturapi (a petición)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account_tax_profile import AccountTaxProfile
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.plan import Plan
from app.services import money
from app.services.facturapi_client import FacturapiClient
from app.services.receipt_pdf import load_receipt_data

_RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
_ZIP_RE = re.compile(r"^\d{5}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SAFE_FOLIO = re.compile(r"[^A-Za-z0-9._-]+")

TAX_SYSTEMS = {
    "601": "General de Ley Personas Morales",
    "603": "Personas Morales con Fines no Lucrativos",
    "605": "Sueldos y Salarios e Ingresos Asimilados a Salarios",
    "606": "Arrendamiento",
    "608": "Demás ingresos",
    "610": "Residentes en el Extranjero sin Establecimiento Permanente en México",
    "611": "Ingresos por Dividendos",
    "612": "Personas Físicas con Actividades Empresariales y Profesionales",
    "614": "Ingresos por intereses",
    "615": "Régimen de los ingresos por obtención de premios",
    "616": "Sin obligaciones fiscales",
    "620": "Sociedades Cooperativas de Producción",
    "621": "Incorporación Fiscal",
    "622": "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras",
    "623": "Opcional para Grupos de Sociedades",
    "624": "Coordinados",
    "625": "Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas",
    "626": "Régimen Simplificado de Confianza",
}

CFDI_USES = {
    "G01": "Adquisición de mercancías",
    "G02": "Devoluciones, descuentos o bonificaciones",
    "G03": "Gastos en general",
    "I01": "Construcciones",
    "I02": "Mobiliario y equipo de oficina",
    "I04": "Equipo de cómputo y accesorios",
    "I08": "Otra maquinaria y equipo",
    "D01": "Honorarios médicos, dentales y gastos hospitalarios",
    "D04": "Donativos",
    "S01": "Sin efectos fiscales",
    "CP01": "Pagos",
}

DEFAULT_CFDI_USE = "G03"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_rfc(raw: str) -> str:
    return re.sub(r"\s+", "", (raw or "").strip().upper().replace("-", ""))


def validate_tax_profile_fields(
    *,
    rfc: str,
    legal_name: str,
    tax_system: str,
    zip_code: str,
    email: str | None,
    default_cfdi_use: str,
) -> dict:
    rfc_n = normalize_rfc(rfc)
    if not _RFC_RE.fullmatch(rfc_n):
        raise HTTPException(400, "RFC inválido.")
    name = (legal_name or "").strip()
    if len(name) < 3:
        raise HTTPException(400, "La razón social es demasiado corta.")
    system = (tax_system or "").strip()
    if system not in TAX_SYSTEMS:
        raise HTTPException(400, "Régimen fiscal no reconocido.")
    zip_n = (zip_code or "").strip()
    if not _ZIP_RE.fullmatch(zip_n):
        raise HTTPException(400, "El código postal debe ser de 5 dígitos.")
    mail = (email or "").strip() or None
    if mail and not _EMAIL_RE.fullmatch(mail):
        raise HTTPException(400, "El correo fiscal no es válido.")
    use = (default_cfdi_use or DEFAULT_CFDI_USE).strip().upper()
    if use not in CFDI_USES:
        raise HTTPException(400, "Uso de CFDI no reconocido.")
    return {
        "rfc": rfc_n,
        "legal_name": name,
        "tax_system": system,
        "zip": zip_n,
        "email": mail,
        "default_cfdi_use": use,
    }


def profile_is_complete(profile: AccountTaxProfile | None) -> bool:
    if profile is None:
        return False
    try:
        validate_tax_profile_fields(
            rfc=profile.rfc,
            legal_name=profile.legal_name,
            tax_system=profile.tax_system,
            zip_code=profile.zip,
            email=profile.email,
            default_cfdi_use=profile.default_cfdi_use,
        )
    except HTTPException:
        return False
    return True


def catalog_items() -> dict[str, list[dict[str, str]]]:
    return {
        "tax_systems": [{"code": k, "name": v} for k, v in TAX_SYSTEMS.items()],
        "cfdi_uses": [{"code": k, "name": v} for k, v in CFDI_USES.items()],
    }


def tax_profile_payload(profile: AccountTaxProfile | None) -> dict:
    catalogs = catalog_items()
    if profile is None:
        return {
            "rfc": None,
            "legal_name": None,
            "tax_system": None,
            "zip": None,
            "email": None,
            "default_cfdi_use": DEFAULT_CFDI_USE,
            "is_complete": False,
            **catalogs,
        }
    return {
        "rfc": profile.rfc,
        "legal_name": profile.legal_name,
        "tax_system": profile.tax_system,
        "zip": profile.zip,
        "email": profile.email,
        "default_cfdi_use": profile.default_cfdi_use or DEFAULT_CFDI_USE,
        "is_complete": profile_is_complete(profile),
        **catalogs,
    }


def get_tax_profile(db: Session, account_id: UUID) -> AccountTaxProfile | None:
    return (
        db.query(AccountTaxProfile)
        .filter(AccountTaxProfile.account_id == account_id)
        .first()
    )


def _customer_payload(fields: dict) -> dict:
    payload = {
        "legal_name": fields["legal_name"],
        "tax_id": fields["rfc"],
        "tax_system": fields["tax_system"],
        "address": {"zip": fields["zip"], "country": "MEX"},
        "default_invoice_use": fields["default_cfdi_use"],
    }
    if fields.get("email"):
        payload["email"] = fields["email"]
    return payload


def upsert_tax_profile(
    db: Session,
    account_id: UUID,
    *,
    rfc: str,
    legal_name: str,
    tax_system: str,
    zip_code: str,
    email: str | None,
    default_cfdi_use: str,
    client: FacturapiClient | None = None,
) -> AccountTaxProfile:
    fields = validate_tax_profile_fields(
        rfc=rfc,
        legal_name=legal_name,
        tax_system=tax_system,
        zip_code=zip_code,
        email=email,
        default_cfdi_use=default_cfdi_use,
    )
    client = client or FacturapiClient()
    live = client.livemode
    profile = get_tax_profile(db, account_id)
    existing_id = None
    if profile is not None and profile.facturapi_livemode == live:
        existing_id = profile.facturapi_customer_id

    remote = client.create_or_update_customer(_customer_payload(fields), existing_id)
    remote_id = remote.get("id")
    if not isinstance(remote_id, str) or not remote_id:
        raise HTTPException(502, "Facturapi no devolvió el cliente fiscal.")

    now = _now()
    if profile is None:
        profile = AccountTaxProfile(account_id=account_id)
        db.add(profile)
    profile.rfc = fields["rfc"]
    profile.legal_name = fields["legal_name"]
    profile.tax_system = fields["tax_system"]
    profile.zip = fields["zip"]
    profile.email = fields["email"]
    profile.default_cfdi_use = fields["default_cfdi_use"]
    profile.facturapi_customer_id = remote_id
    profile.facturapi_livemode = live
    profile.updated_at = now
    db.commit()
    db.refresh(profile)
    return profile


def _ensure_customer(
    db: Session,
    profile: AccountTaxProfile,
    client: FacturapiClient,
) -> str:
    live = client.livemode
    if profile.facturapi_customer_id and profile.facturapi_livemode == live:
        return profile.facturapi_customer_id
    remote = client.create_or_update_customer(
        _customer_payload(
            {
                "rfc": profile.rfc,
                "legal_name": profile.legal_name,
                "tax_system": profile.tax_system,
                "zip": profile.zip,
                "email": profile.email,
                "default_cfdi_use": profile.default_cfdi_use or DEFAULT_CFDI_USE,
            }
        ),
        None,
    )
    remote_id = remote.get("id")
    if not isinstance(remote_id, str) or not remote_id:
        raise HTTPException(502, "Facturapi no devolvió el cliente fiscal.")
    profile.facturapi_customer_id = remote_id
    profile.facturapi_livemode = live
    profile.updated_at = _now()
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return remote_id


def _payment_form(payment: Payment | None) -> str:
    if payment is not None and (payment.gateway or "").lower() == "manual":
        return "01"
    return "04"


def _item_description(db: Session, invoice: Invoice, payment: Payment | None) -> str:
    extra = (payment.extra_data or {}) if payment else {}
    plan_id = extra.get("plan_id")
    if plan_id:
        try:
            plan = db.query(Plan).filter(Plan.id == UUID(str(plan_id))).first()
        except (TypeError, ValueError):
            plan = None
        if plan and plan.name:
            cycle = (extra.get("billing_cycle") or "").upper()
            period = "anual" if cycle == "YEARLY" else "mensual"
            return f"{plan.name} · suscripción {period}"
    return "Suscripción NEXUS"


def _extract_uuid(remote: dict) -> str | None:
    uuid = remote.get("uuid")
    if isinstance(uuid, str) and uuid.strip():
        return uuid.strip()
    stamp = remote.get("stamp")
    if isinstance(stamp, dict):
        uuid = stamp.get("uuid")
        if isinstance(uuid, str) and uuid.strip():
            return uuid.strip()
    return None


def stamp_cfdi(
    db: Session,
    invoice: Invoice,
    *,
    cfdi_use: str | None = None,
    client: FacturapiClient | None = None,
) -> Invoice:
    if invoice.cfdi_uuid:
        return invoice
    paid = invoice.invoice_status == InvoiceStatus.PAID.value or bool(invoice.paid_at)
    if not paid:
        raise HTTPException(409, "Solo se puede facturar un cobro ya acreditado.")

    profile = get_tax_profile(db, invoice.account_id)
    if not profile_is_complete(profile):
        raise HTTPException(
            409,
            "Completa los datos fiscales (RFC, razón social, régimen y CP) antes de facturar.",
        )
    assert profile is not None

    use = (cfdi_use or profile.default_cfdi_use or DEFAULT_CFDI_USE).strip().upper()
    if use not in CFDI_USES:
        raise HTTPException(400, "Uso de CFDI no reconocido.")

    client = client or FacturapiClient()
    customer_id = _ensure_customer(db, profile, client)
    _, payment = load_receipt_data(db, invoice)
    total = money.parse(invoice.total_amount or 0)
    if total <= Decimal("0"):
        raise HTTPException(400, "El importe de la factura no es facturable.")

    payload = {
        "customer": customer_id,
        "items": [
            {
                "quantity": 1,
                "product": {
                    "description": _item_description(db, invoice, payment),
                    "product_key": settings.FACTURAPI_PRODUCT_KEY,
                    "unit_key": settings.FACTURAPI_UNIT_KEY,
                    "price": float(money.dump(total)),
                    "tax_included": True,
                },
            }
        ],
        "use": use,
        "payment_form": _payment_form(payment),
        "payment_method": "PUE",
        "external_id": str(invoice.id),
        "idempotency_key": str(invoice.id),
        "pdf_options": {"round_unit_price": True},
    }
    remote = client.create_invoice(payload)
    if not isinstance(remote, dict):
        raise HTTPException(502, "Facturapi no devolvió el CFDI.")
    uuid = _extract_uuid(remote)
    if not uuid:
        raise HTTPException(
            502,
            "Facturapi no devolvió el UUID del CFDI. Intenta de nuevo en un momento.",
        )
    remote_id = remote.get("id")
    extra = dict(invoice.extra_data or {})
    if isinstance(remote_id, str) and remote_id:
        extra["facturapi_invoice_id"] = remote_id
    extra["cfdi_use"] = use
    invoice.extra_data = extra
    invoice.cfdi_uuid = uuid
    invoice.updated_at = _now()
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def facturapi_invoice_id(invoice: Invoice) -> str | None:
    stored = (invoice.extra_data or {}).get("facturapi_invoice_id")
    return stored if isinstance(stored, str) and stored else None


def download_cfdi_file(
    invoice: Invoice,
    fmt: str,
    *,
    client: FacturapiClient | None = None,
) -> bytes:
    remote_id = facturapi_invoice_id(invoice)
    if not invoice.cfdi_uuid or not remote_id:
        raise HTTPException(409, "Esta factura aún no tiene CFDI timbrado.")
    client = client or FacturapiClient()
    return client.get_invoice_file(remote_id, fmt)


def cfdi_filename(invoice_number: str, fmt: str) -> str:
    folio = _SAFE_FOLIO.sub("-", invoice_number or "cfdi").strip("-") or "cfdi"
    return f"cfdi-{folio}.{fmt}"
