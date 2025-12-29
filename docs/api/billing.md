# API de Billing (Facturación)

## Descripción

Endpoints **READ-ONLY** para consultar información de facturación y pagos de una organización.

> **IMPORTANTE**: Estos endpoints son **INFORMATIVOS** y de solo lectura.
> No implementan lógica de cobro ni procesamiento de pagos.

---

## Estado de Implementación

### ✅ Implementado (Informativo)
- Resumen de facturación (`/billing/summary`)
- Historial de pagos (`/billing/payments`)
- Lista de invoices (`/billing/invoices`) - stub provisional

### 🔜 Futuro (Cuando se integre PSP)
- Procesamiento de pagos
- Generación de invoices reales
- Métodos de pago guardados
- Webhooks de pago

### 📝 Notas de Implementación

```
ESTADO ACTUAL:
┌─────────────────────────────────────────────────────────────┐
│  Los datos vienen de:                                        │
│  - Tabla `payments` → pagos registrados                     │
│  - Tabla `subscriptions` → contexto de suscripciones        │
│  - Tabla `clients` → información de organización            │
│                                                              │
│  Los invoices son STUBS generados a partir de payments      │
│  exitosos. Cuando se integre Stripe/PSP, vendrán de ahí.    │
└─────────────────────────────────────────────────────────────┘
```

### ⚠️ Múltiples Suscripciones Activas

> **Regla de selección**: Si una organización tiene múltiples suscripciones activas, el sistema considera como **plan actual** el correspondiente a la suscripción activa más reciente (por `started_at`).

Esto aplica **solo para billing y UI**. Las capabilities se resuelven de forma independiente y pueden incluir overrides específicos de la organización.

---

## Endpoints

### 1. Resumen de Facturación

**GET** `/api/v1/billing/summary`

Obtiene un resumen completo del estado de facturación de la organización.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "organization_id": "456e4567-e89b-12d3-a456-426614174000",
  "organization_name": "Transportes XYZ",
  "has_active_subscription": true,
  "current_plan": {
    "plan_id": "123e4567-e89b-12d3-a456-426614174000",
    "plan_name": "Plan Profesional",
    "plan_code": "pro",
    "billing_cycle": "MONTHLY",
    "next_billing_date": "2024-02-01T00:00:00Z",
    "amount_due": "599.00",
    "currency": "MXN"
  },
  "pending_amount": "0.00",
  "stats": {
    "total_paid": "7188.00",
    "payments_count": 12,
    "last_payment_date": "2024-01-15T10:30:00Z",
    "last_payment_amount": "599.00",
    "currency": "MXN"
  },
  "billing_email": "facturacion@transportesxyz.com"
}
```

#### Campos del Response

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `organization_id` | UUID | ID de la organización |
| `organization_name` | string | Nombre de la organización |
| `has_active_subscription` | bool | Si tiene suscripción activa |
| `current_plan` | object/null | Info del plan actual (si hay suscripción) |
| `pending_amount` | decimal | Monto pendiente de pago |
| `stats` | object | Estadísticas de pagos históricos |
| `billing_email` | string/null | Email de facturación configurado |

#### Notas

- `current_plan.next_billing_date` se obtiene de `subscription.expires_at`
- `pending_amount` suma los pagos con status `PENDING`
- `stats.total_paid` solo cuenta pagos con status `SUCCESS`

---

### 2. Historial de Pagos

**GET** `/api/v1/billing/payments`

Lista el historial de pagos de la organización.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Máximo de resultados (máx 100) |
| `offset` | int | 0 | Offset para paginación |
| `status` | enum | null | Filtrar por estado (SUCCESS, FAILED, PENDING, REFUNDED) |

#### Response 200 OK

```json
{
  "payments": [
    {
      "id": "789e4567-e89b-12d3-a456-426614174000",
      "amount": "599.00",
      "currency": "MXN",
      "method": "card",
      "status": "SUCCESS",
      "paid_at": "2024-01-15T10:30:00Z",
      "transaction_ref": "txn_abc123xyz",
      "invoice_url": "https://example.com/invoices/123.pdf",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "890e4567-e89b-12d3-a456-426614174001",
      "amount": "599.00",
      "currency": "MXN",
      "method": "card",
      "status": "SUCCESS",
      "paid_at": "2023-12-15T10:30:00Z",
      "transaction_ref": "txn_def456abc",
      "invoice_url": "https://example.com/invoices/122.pdf",
      "created_at": "2023-12-15T10:30:00Z"
    }
  ],
  "total": 12,
  "has_more": true
}
```

#### Estados de Pago

| Estado | Descripción |
|--------|-------------|
| `SUCCESS` | Pago exitoso |
| `FAILED` | Pago fallido |
| `PENDING` | Pago pendiente de procesamiento |
| `REFUNDED` | Pago reembolsado |

---

### 3. Lista de Invoices/Facturas

**GET** `/api/v1/billing/invoices`

Lista las facturas de la organización.

> **⚠️ STUB PROVISIONAL**: Actualmente los invoices se generan a partir de pagos exitosos. Cuando se integre un PSP como Stripe, los invoices vendrán directamente de ahí.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Máximo de resultados (máx 100) |
| `offset` | int | 0 | Offset para paginación |

#### Response 200 OK

```json
{
  "invoices": [
    {
      "id": "789e4567-e89b-12d3-a456-426614174000",
      "invoice_number": "INV-2024-0012",
      "status": "PAID",
      "amount": "599.00",
      "currency": "MXN",
      "description": "Suscripción SISCOM",
      "created_at": "2024-01-01T00:00:00Z",
      "paid_at": "2024-01-15T10:30:00Z",
      "due_date": null,
      "invoice_url": "https://example.com/invoices/123.pdf",
      "payment_id": "789e4567-e89b-12d3-a456-426614174000",
      "subscription_id": null
    },
    {
      "id": "890e4567-e89b-12d3-a456-426614174001",
      "invoice_number": "INV-2024-0011",
      "status": "PAID",
      "amount": "599.00",
      "currency": "MXN",
      "description": "Suscripción SISCOM",
      "created_at": "2023-12-01T00:00:00Z",
      "paid_at": "2023-12-15T10:30:00Z",
      "due_date": null,
      "invoice_url": "https://example.com/invoices/122.pdf",
      "payment_id": "890e4567-e89b-12d3-a456-426614174001",
      "subscription_id": null
    }
  ],
  "total": 12,
  "has_more": true
}
```

#### Estados de Invoice

| Estado | Descripción |
|--------|-------------|
| `DRAFT` | Borrador (no emitida) |
| `PENDING` | Pendiente de pago |
| `PAID` | Pagada |
| `VOID` | Anulada |
| `OVERDUE` | Vencida sin pago |

#### Notas de Implementación

- Actualmente solo muestra invoices con status `PAID`
- El `invoice_number` se genera automáticamente (formato: `INV-YYYY-NNNN`)
- `invoice_url` es la URL de la factura/recibo si está disponible
- `subscription_id` actualmente es `null` (no hay relación directa en el modelo)

---

## Flujos de Uso

### Frontend: Mostrar Estado de Cuenta

```
1. GET /billing/summary
   → Obtener resumen con plan actual y estadísticas

2. Mostrar:
   - Plan actual y próxima fecha de cobro
   - Total histórico pagado
   - Monto pendiente (si existe)
```

### Frontend: Mostrar Historial de Pagos

```
1. GET /billing/payments?limit=10
   → Primeros 10 pagos

2. Si has_more = true y usuario quiere ver más:
   GET /billing/payments?limit=10&offset=10
   → Siguientes 10 pagos
```

### Frontend: Descargar Facturas

```
1. GET /billing/invoices
   → Lista de invoices con URLs

2. Para cada invoice con invoice_url:
   → Mostrar botón "Descargar" que abre la URL
```

---

## Integración Futura con PSP

Cuando se integre un PSP como Stripe:

### Cambios Esperados

| Actual | Futuro |
|--------|--------|
| Invoices generados de payments | Invoices de Stripe Invoice API |
| `invoice_url` manual | URL de Stripe hosted invoice |
| Sin métodos de pago guardados | Customer payment methods |
| Sin renovación automática real | Stripe Billing automation |

### Endpoints Adicionales (Futuro)

```
POST /billing/payment-methods     # Agregar método de pago
GET  /billing/payment-methods     # Listar métodos guardados
DELETE /billing/payment-methods/{id}  # Eliminar método

POST /billing/create-checkout     # Crear sesión de pago
POST /billing/portal              # Abrir Stripe Customer Portal
```

---

## Relación con Otros Endpoints

```
┌─────────────────────────────────────────────────────────────┐
│                    BILLING                                   │
│  (informativo, read-only)                                   │
├─────────────────────────────────────────────────────────────┤
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │  SUBSCRIPTIONS  │◄───│     PLANS       │                │
│  │  (operativo)    │    │  (informativo)  │                │
│  └────────┬────────┘    └─────────────────┘                │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │  CAPABILITIES   │                                        │
│  │  (fuente de     │                                        │
│  │   verdad)       │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Ejemplos de Uso

### cURL: Obtener Resumen

```bash
curl -X GET "http://localhost:8000/api/v1/billing/summary" \
  -H "Authorization: Bearer <token>"
```

### cURL: Listar Pagos Exitosos

```bash
curl -X GET "http://localhost:8000/api/v1/billing/payments?status=SUCCESS&limit=10" \
  -H "Authorization: Bearer <token>"
```

### cURL: Listar Invoices

```bash
curl -X GET "http://localhost:8000/api/v1/billing/invoices?limit=20" \
  -H "Authorization: Bearer <token>"
```

---

**Última actualización**: Diciembre 2025  
**Estado**: Implementación inicial (read-only, sin PSP)  
**Referencia**: [API de Subscriptions](subscriptions.md) | [API de Plans](plans.md)

