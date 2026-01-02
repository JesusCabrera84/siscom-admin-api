"""
Endpoints de Billing (Read-Only).

Expone información de facturación y pagos de forma estructurada
para que el frontend pueda mostrar:
- Resumen de estado de facturación
- Historial de pagos
- Invoices/facturas (provisional)

IMPORTANTE:
-----------
Estos endpoints son READ-ONLY. No implementan lógica de cobro.
La integración con PSP (Stripe, etc.) se hará posteriormente.

Actualmente la información se obtiene de:
- Tabla payments: pagos registrados
- Tabla subscriptions: contexto de suscripciones
- Tabla organizations: información de la organización
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.organization import Organization
from app.models.payment import Payment, PaymentStatus
from app.models.plan import Plan
from app.schemas.billing import (
    BillingStats,
    BillingSummaryOut,
    CurrentPlanInfo,
    InvoiceOut,
    InvoicesListOut,
    InvoiceStatus,
    PaymentOut,
    PaymentsListOut,
)
from app.services.subscription_query import get_primary_active_subscription

router = APIRouter()


def _get_billing_stats(db: Session, organization_id: UUID) -> BillingStats:
    """
    Calcula estadísticas de facturación para una organización.
    """
    # Total pagado (solo SUCCESS)
    total_result = (
        db.query(func.sum(Payment.amount))
        .filter(
            Payment.client_id == organization_id,
            Payment.status == PaymentStatus.SUCCESS.value,
        )
        .scalar()
    )
    total_paid = Decimal(total_result or 0)

    # Conteo de pagos exitosos
    payments_count = (
        db.query(Payment)
        .filter(
            Payment.client_id == organization_id,
            Payment.status == PaymentStatus.SUCCESS.value,
        )
        .count()
    )

    # Último pago
    last_payment = (
        db.query(Payment)
        .filter(
            Payment.client_id == organization_id,
            Payment.status == PaymentStatus.SUCCESS.value,
        )
        .order_by(Payment.paid_at.desc())
        .first()
    )

    return BillingStats(
        total_paid=total_paid,
        payments_count=payments_count,
        last_payment_date=last_payment.paid_at if last_payment else None,
        last_payment_amount=last_payment.amount if last_payment else None,
        currency="MXN",
    )


def _get_pending_amount(db: Session, organization_id: UUID) -> Decimal:
    """
    Calcula el monto pendiente de pago.
    """
    pending_result = (
        db.query(func.sum(Payment.amount))
        .filter(
            Payment.client_id == organization_id,
            Payment.status == PaymentStatus.PENDING.value,
        )
        .scalar()
    )
    return Decimal(pending_result or 0)


@router.get("/summary", response_model=BillingSummaryOut)
def get_billing_summary(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene el resumen de facturación de la organización.

    Incluye:
    - Estado de la suscripción actual
    - Información del plan y próximo cobro
    - Estadísticas de pagos históricos
    - Balance pendiente

    Notas:
        - Este endpoint es READ-ONLY
        - La integración con PSP aún no está implementada
        - next_billing_date se obtiene de subscription.expires_at
    """
    # Obtener organización
    organization = (
        db.query(Organization).filter(Organization.id == organization_id).first()
    )

    # Obtener suscripción activa principal
    active_sub = get_primary_active_subscription(db, organization_id)

    current_plan = None
    if active_sub:
        plan = db.query(Plan).filter(Plan.id == active_sub.plan_id).first()
        if plan:
            # Determinar el monto según el ciclo
            amount_due = plan.price_monthly
            if active_sub.billing_cycle == "YEARLY":
                amount_due = plan.price_yearly

            current_plan = CurrentPlanInfo(
                plan_id=plan.id,
                plan_name=plan.name,
                plan_code=plan.code,
                billing_cycle=active_sub.billing_cycle or "MONTHLY",
                next_billing_date=active_sub.expires_at,
                amount_due=amount_due,
                currency="MXN",
            )

    # Estadísticas
    stats = _get_billing_stats(db, organization_id)
    pending_amount = _get_pending_amount(db, organization_id)

    return BillingSummaryOut(
        organization_id=organization_id,
        organization_name=organization.name if organization else "Unknown",
        has_active_subscription=active_sub is not None,
        current_plan=current_plan,
        pending_amount=pending_amount,
        stats=stats,
        billing_email=organization.billing_email if organization else None,
    )


@router.get("/payments", response_model=PaymentsListOut)
def list_payments(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100, description="Máximo de resultados"),
    offset: int = Query(default=0, ge=0, description="Offset para paginación"),
    status: PaymentStatus | None = Query(
        default=None, description="Filtrar por estado"
    ),
):
    """
    Lista el historial de pagos de la organización.

    Args:
        limit: Número máximo de resultados (máx 100)
        offset: Offset para paginación
        status: Filtrar por estado de pago (opcional)

    Returns:
        Lista de pagos ordenados por fecha (más reciente primero)

    Notas:
        - Los pagos pueden venir de integración manual o futura integración con PSP
        - invoice_url apunta a la factura cuando está disponible
    """
    query = db.query(Payment).filter(Payment.client_id == organization_id)

    if status:
        query = query.filter(Payment.status == status.value)

    # Total sin paginación
    total = query.count()

    # Aplicar paginación
    payments = (
        query.order_by(Payment.created_at.desc()).limit(limit).offset(offset).all()
    )

    payments_out = [PaymentOut.model_validate(p) for p in payments]

    return PaymentsListOut(
        payments=payments_out, total=total, has_more=(offset + len(payments)) < total
    )


@router.get("/invoices", response_model=InvoicesListOut)
def list_invoices(
    organization_id: UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100, description="Máximo de resultados"),
    offset: int = Query(default=0, ge=0, description="Offset para paginación"),
):
    """
    Lista las facturas/invoices de la organización.

    NOTA IMPORTANTE:
    ----------------
    Este endpoint es PROVISIONAL. Actualmente genera invoices
    a partir de los pagos exitosos (payments con status=SUCCESS).

    Cuando se integre un PSP como Stripe, las invoices vendrán
    directamente de la API del PSP y este endpoint se actualizará.

    Args:
        limit: Número máximo de resultados (máx 100)
        offset: Offset para paginación

    Returns:
        Lista de invoices ordenadas por fecha (más reciente primero)
    """
    # Obtener pagos exitosos como "invoices"
    query = db.query(Payment).filter(
        Payment.client_id == organization_id,
        Payment.status == PaymentStatus.SUCCESS.value,
    )

    total = query.count()

    payments = query.order_by(Payment.paid_at.desc()).limit(limit).offset(offset).all()

    # Convertir payments a invoices
    invoices = []
    for i, payment in enumerate(payments):
        # Generar número de invoice basado en fecha y secuencia
        invoice_date = payment.paid_at or payment.created_at
        year = invoice_date.year if invoice_date else datetime.utcnow().year

        # Número secuencial (simplificado, en producción vendría del PSP)
        seq = total - offset - i
        invoice_number = f"INV-{year}-{seq:04d}"

        invoice = InvoiceOut(
            id=payment.id,
            invoice_number=invoice_number,
            status=InvoiceStatus.PAID,  # Solo mostramos pagos exitosos
            amount=payment.amount,
            currency=payment.currency or "MXN",
            description="Suscripción SISCOM",
            created_at=payment.created_at,
            paid_at=payment.paid_at,
            due_date=None,  # No hay due_date en el modelo actual
            invoice_url=payment.invoice_url,
            payment_id=payment.id,
            subscription_id=None,  # No hay relación directa en el modelo actual
        )
        invoices.append(invoice)

    return InvoicesListOut(
        invoices=invoices, total=total, has_more=(offset + len(invoices)) < total
    )
