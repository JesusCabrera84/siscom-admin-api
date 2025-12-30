"""
Schemas para Billing (Read-Only).

Estos schemas representan información de facturación y pagos.
Son INFORMATIVOS y de solo lectura.

NOTA IMPORTANTE:
----------------
La integración con PSP (Stripe, etc.) NO está implementada.
Los endpoints de billing muestran información provisional basada en:
- Tabla payments (pagos registrados)
- Tabla subscriptions (para contexto de suscripciones)

Cuando se integre un PSP, estos schemas pueden extenderse
sin romper la API existente.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus


class InvoiceStatus(str, Enum):
    """Estados posibles de una factura/invoice."""

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PAID = "PAID"
    VOID = "VOID"
    OVERDUE = "OVERDUE"


class PaymentMethod(str, Enum):
    """Métodos de pago soportados."""

    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    OTHER = "other"


# ============================================
# Billing Summary
# ============================================


class CurrentPlanInfo(BaseModel):
    """Información del plan actual."""

    plan_id: UUID
    plan_name: str
    plan_code: str
    billing_cycle: str
    next_billing_date: Optional[datetime] = Field(
        None, description="Próxima fecha de facturación"
    )
    amount_due: Decimal = Field(..., description="Monto a cobrar en el próximo ciclo")
    currency: str = "MXN"

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "123e4567-e89b-12d3-a456-426614174000",
                "plan_name": "Plan Profesional",
                "plan_code": "pro",
                "billing_cycle": "MONTHLY",
                "next_billing_date": "2024-02-01T00:00:00Z",
                "amount_due": "599.00",
                "currency": "MXN",
            }
        }


class BillingStats(BaseModel):
    """Estadísticas de facturación."""

    total_paid: Decimal = Field(..., description="Total pagado históricamente")
    payments_count: int = Field(..., description="Número total de pagos")
    last_payment_date: Optional[datetime] = Field(
        None, description="Fecha del último pago"
    )
    last_payment_amount: Optional[Decimal] = Field(
        None, description="Monto del último pago"
    )
    currency: str = "MXN"

    class Config:
        json_schema_extra = {
            "example": {
                "total_paid": "7188.00",
                "payments_count": 12,
                "last_payment_date": "2024-01-15T10:30:00Z",
                "last_payment_amount": "599.00",
                "currency": "MXN",
            }
        }


class BillingSummaryOut(BaseModel):
    """
    Resumen completo de facturación para una organización.

    Incluye:
    - Estado de la suscripción actual
    - Próximo cobro
    - Estadísticas de pagos
    - Balance pendiente
    """

    organization_id: UUID
    organization_name: str

    # Estado actual
    has_active_subscription: bool = Field(
        ..., description="Si tiene suscripción activa"
    )
    current_plan: Optional[CurrentPlanInfo] = Field(
        None, description="Información del plan actual (si hay suscripción activa)"
    )

    # Balance
    pending_amount: Decimal = Field(
        default=Decimal("0.00"), description="Monto pendiente de pago"
    )

    # Estadísticas
    stats: BillingStats

    # Metadata
    billing_email: Optional[str] = Field(
        None, description="Email de facturación configurado"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "456e4567-e89b-12d3-a456-426614174000",
                "organization_name": "Transportes XYZ",
                "has_active_subscription": True,
                "current_plan": {
                    "plan_id": "123e4567-e89b-12d3-a456-426614174000",
                    "plan_name": "Plan Profesional",
                    "plan_code": "pro",
                    "billing_cycle": "MONTHLY",
                    "next_billing_date": "2024-02-01T00:00:00Z",
                    "amount_due": "599.00",
                    "currency": "MXN",
                },
                "pending_amount": "0.00",
                "stats": {
                    "total_paid": "7188.00",
                    "payments_count": 12,
                    "last_payment_date": "2024-01-15T10:30:00Z",
                    "last_payment_amount": "599.00",
                    "currency": "MXN",
                },
                "billing_email": "facturacion@transportesxyz.com",
            }
        }


# ============================================
# Payments
# ============================================


class PaymentOut(BaseModel):
    """Pago individual."""

    id: UUID
    amount: Decimal
    currency: str = "MXN"
    method: Optional[str] = None
    status: PaymentStatus
    paid_at: Optional[datetime] = None
    transaction_ref: Optional[str] = Field(
        None, description="Referencia de transacción (PSP)"
    )
    invoice_url: Optional[str] = Field(None, description="URL de la factura/recibo")
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "789e4567-e89b-12d3-a456-426614174000",
                "amount": "599.00",
                "currency": "MXN",
                "method": "card",
                "status": "SUCCESS",
                "paid_at": "2024-01-15T10:30:00Z",
                "transaction_ref": "txn_abc123xyz",
                "invoice_url": "https://example.com/invoices/123.pdf",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class PaymentsListOut(BaseModel):
    """Lista de pagos con paginación."""

    payments: list[PaymentOut]
    total: int
    has_more: bool = Field(..., description="Si hay más pagos disponibles")

    class Config:
        json_schema_extra = {
            "example": {
                "payments": [
                    {
                        "id": "789e4567-e89b-12d3-a456-426614174000",
                        "amount": "599.00",
                        "currency": "MXN",
                        "method": "card",
                        "status": "SUCCESS",
                        "paid_at": "2024-01-15T10:30:00Z",
                        "transaction_ref": "txn_abc123xyz",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total": 12,
                "has_more": True,
            }
        }


# ============================================
# Invoices (Stub - Provisional)
# ============================================


class InvoiceOut(BaseModel):
    """
    Factura/Invoice (STUB PROVISIONAL).

    NOTA: Este schema es provisional. Actualmente se genera
    a partir de la tabla payments. Cuando se integre un PSP
    como Stripe, las invoices vendrán directamente de él.
    """

    id: UUID = Field(..., description="ID del invoice (actualmente = payment_id)")
    invoice_number: str = Field(..., description="Número de factura para mostrar")
    status: InvoiceStatus
    amount: Decimal
    currency: str = "MXN"
    description: str = Field(
        default="Suscripción SISCOM", description="Descripción del concepto"
    )

    # Fechas
    created_at: datetime
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = Field(
        None, description="Fecha de vencimiento (si aplica)"
    )

    # URLs
    invoice_url: Optional[str] = Field(
        None, description="URL para descargar/ver la factura"
    )

    # Relaciones
    payment_id: Optional[UUID] = Field(None, description="ID del pago asociado")
    subscription_id: Optional[UUID] = Field(
        None, description="ID de la suscripción asociada"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "789e4567-e89b-12d3-a456-426614174000",
                "invoice_number": "INV-2024-0001",
                "status": "PAID",
                "amount": "599.00",
                "currency": "MXN",
                "description": "Suscripción SISCOM - Plan Profesional (Enero 2024)",
                "created_at": "2024-01-01T00:00:00Z",
                "paid_at": "2024-01-15T10:30:00Z",
                "due_date": "2024-01-15T00:00:00Z",
                "invoice_url": "https://example.com/invoices/INV-2024-0001.pdf",
                "payment_id": "789e4567-e89b-12d3-a456-426614174000",
                "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }


class InvoicesListOut(BaseModel):
    """
    Lista de invoices (STUB PROVISIONAL).

    Actualmente se genera a partir de payments exitosos.
    """

    invoices: list[InvoiceOut]
    total: int
    has_more: bool

    class Config:
        json_schema_extra = {
            "example": {
                "invoices": [
                    {
                        "id": "789e4567-e89b-12d3-a456-426614174000",
                        "invoice_number": "INV-2024-0001",
                        "status": "PAID",
                        "amount": "599.00",
                        "currency": "MXN",
                        "description": "Suscripción SISCOM - Plan Profesional",
                        "created_at": "2024-01-01T00:00:00Z",
                        "paid_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total": 12,
                "has_more": True,
            }
        }
