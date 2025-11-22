# API de Pagos

## Descripción

Endpoints para gestionar y consultar pagos realizados por el cliente. Los pagos pueden ser por órdenes de dispositivos o por servicios de rastreo.

---

## Endpoints

### 1. Listar Pagos

**GET** `/api/v1/payments/`

Lista todos los pagos del cliente autenticado, ordenados por fecha (más reciente primero).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
[
  {
    "id": "abc12345-e89b-12d3-a456-426614174000",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "amount": 299.0,
    "status": "SUCCESS",
    "payment_method": "credit_card",
    "description": "Plan Premium - Suscripción Mensual",
    "device_service_id": "323e4567-e89b-12d3-a456-426614174000",
    "order_id": null,
    "created_at": "2024-01-15T10:30:00Z",
    "paid_at": "2024-01-15T10:30:15Z"
  },
  {
    "id": "def67890-e89b-12d3-a456-426614174000",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "amount": 5000.0,
    "status": "SUCCESS",
    "payment_method": "bank_transfer",
    "description": "Orden #789e4567",
    "device_service_id": null,
    "order_id": "789e4567-e89b-12d3-a456-426614174000",
    "created_at": "2024-01-10T14:00:00Z",
    "paid_at": "2024-01-10T14:05:00Z"
  }
]
```

---

## Estados del Pago

### PENDING

- Pago creado, esperando confirmación
- Gateway de pago procesando
- Cliente puede cancelar

### SUCCESS

- Pago confirmado exitosamente
- Fondos recibidos
- Servicio/orden activado

### FAILED

- Pago rechazado o fallido
- Fondos no recibidos
- Cliente debe intentar nuevamente

### REFUNDED

- Pago reembolsado
- Fondos devueltos al cliente
- Servicio/orden cancelado

---

## Tipos de Pago

### 1. Pago de Servicio

Pago por activación o renovación de servicio de rastreo:

```json
{
  "amount": 299.0,
  "description": "Plan Premium - Suscripción Mensual",
  "device_service_id": "323e4567-e89b-12d3-a456-426614174000",
  "order_id": null
}
```

### 2. Pago de Orden

Pago por compra de dispositivos GPS:

```json
{
  "amount": 5000.0,
  "description": "Orden #789e4567 - 2x TK103, 1x TK303",
  "device_service_id": null,
  "order_id": "789e4567-e89b-12d3-a456-426614174000"
}
```

---

## Métodos de Pago

### Tarjeta de Crédito/Débito

```json
{
  "payment_method": "credit_card",
  "payment_details": {
    "card_brand": "visa",
    "last_four": "4242"
  }
}
```

### Transferencia Bancaria

```json
{
  "payment_method": "bank_transfer",
  "payment_details": {
    "bank": "BBVA",
    "reference": "1234567890"
  }
}
```

### Otros Métodos

- `paypal`
- `oxxo` (México)
- `mercadopago` (Latinoamérica)
- `stripe`

---

## Relaciones del Pago

### Con Servicio de Dispositivo

```
Payment → DeviceService
  - payment.device_service_id = device_service.id
  - Representa pago de suscripción mensual/anual
```

### Con Orden

```
Payment → Order
  - payment.order_id = order.id
  - Representa pago de compra de hardware
```

**Nota**: Un pago está asociado a un servicio O a una orden, nunca a ambos.

---

## Flujo de Pago - Servicio

### 1. Cliente Activa Servicio

```bash
POST /api/v1/services/activate
{
  "device_id": "...",
  "plan_id": "...",
  "subscription_type": "MONTHLY"
}
```

### 2. Sistema Crea Pago

```
Payment.status = PENDING (o SUCCESS si simulado)
Payment.amount = Plan.monthly_price
Payment.device_service_id = DeviceService.id
```

### 3. Cliente Paga (Gateway)

```
Redirección a Stripe/MercadoPago
Cliente completa pago
Webhook notifica resultado
```

### 4. Webhook Actualiza Pago

```
Payment.status = SUCCESS
Payment.paid_at = NOW()
DeviceService.status = ACTIVE
```

---

## Flujo de Pago - Orden

### 1. Cliente Crea Orden

```bash
POST /api/v1/orders/
{
  "items": [...]
}
```

### 2. Sistema Crea Pago

```
Payment.status = PENDING
Payment.amount = Order.total_amount
Payment.order_id = Order.id
```

### 3. Cliente Paga

```
Gateway de pago procesa
```

### 4. Pago Confirmado

```
Payment.status = SUCCESS
Order.status = PAID
```

---

## Webhook de Gateway de Pago

### Ejemplo: Stripe Webhook

```python
@router.post("/webhooks/stripe")
def stripe_webhook(payload: dict):
    event = payload["type"]

    if event == "payment_intent.succeeded":
        payment_id = payload["data"]["object"]["metadata"]["payment_id"]

        # Actualizar pago
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        payment.status = PaymentStatus.SUCCESS
        payment.paid_at = datetime.utcnow()
        db.commit()

        # Activar servicio o completar orden
        if payment.device_service_id:
            activate_service(payment.device_service_id)
        elif payment.order_id:
            mark_order_as_paid(payment.order_id)

    return {"status": "received"}
```

---

## Campos del Pago

### Campos Obligatorios

- `amount`: Monto del pago (decimal)
- `status`: Estado del pago (PENDING, SUCCESS, FAILED, REFUNDED)
- `client_id`: Cliente que realiza el pago

### Campos Opcionales

- `payment_method`: Método de pago utilizado
- `description`: Descripción del pago
- `device_service_id`: Si es pago de servicio
- `order_id`: Si es pago de orden
- `paid_at`: Fecha y hora del pago exitoso

---

## Reembolsos

### Solicitar Reembolso

```python
# Actualizar pago
payment.status = PaymentStatus.REFUNDED
payment.refunded_at = datetime.utcnow()

# Si es servicio, cancelar
if payment.device_service_id:
    service.status = DeviceServiceStatus.CANCELLED
    service.cancelled_at = datetime.utcnow()

# Si es orden, cancelar
if payment.order_id:
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
```

### Validaciones para Reembolso

- Solo pagos `SUCCESS` pueden reembolsarse
- Validar política de reembolso (ej: 30 días)
- Para servicios: validar si ya se consumió el servicio
- Para órdenes: validar si ya se enviaron dispositivos

---

## Reportes de Pagos

### Ingresos Mensuales

```sql
SELECT
  DATE_TRUNC('month', paid_at) as month,
  SUM(amount) as total_revenue
FROM payments
WHERE status = 'SUCCESS'
  AND client_id = '...'
GROUP BY month
ORDER BY month DESC;
```

### Pagos por Método

```sql
SELECT
  payment_method,
  COUNT(*) as count,
  SUM(amount) as total
FROM payments
WHERE status = 'SUCCESS'
  AND client_id = '...'
GROUP BY payment_method;
```

### Tasa de Éxito

```sql
SELECT
  COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END)::float / COUNT(*) * 100 as success_rate
FROM payments
WHERE client_id = '...';
```

---

## Consideraciones de Seguridad

### Información Sensible

- **NO** almacenar números de tarjeta completos
- Solo guardar últimos 4 dígitos (para referencia)
- Usar tokens de gateway de pago

### PCI Compliance

- El procesamiento de pagos debe hacerse a través de gateway certificado
- No manejar datos de tarjetas directamente
- Usar Stripe, PayPal, MercadoPago, etc.

### Validación de Webhooks

```python
def validate_webhook(payload, signature):
    # Validar que el webhook viene del gateway
    expected_signature = calculate_signature(payload, secret_key)
    return signature == expected_signature
```

---

## Integración con Gateways

### Stripe

```python
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

# Crear intención de pago
intent = stripe.PaymentIntent.create(
    amount=int(payment.amount * 100),  # En centavos
    currency="mxn",
    metadata={"payment_id": str(payment.id)}
)

return {"client_secret": intent.client_secret}
```

### MercadoPago

```python
import mercadopago

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

# Crear preferencia de pago
preference = sdk.preference().create({
    "items": [{
        "title": payment.description,
        "quantity": 1,
        "unit_price": float(payment.amount)
    }],
    "external_reference": str(payment.id)
})

return {"init_point": preference["response"]["init_point"]}
```

---

## Ejemplo Completo

### 1. Activar Servicio (crea pago automático)

```bash
POST /api/v1/services/activate
```

### 2. Consultar Pagos

```bash
GET /api/v1/payments/
```

### 3. Ver Detalle de Pago

```json
{
  "id": "abc123...",
  "amount": 299.0,
  "status": "SUCCESS",
  "description": "Plan Premium - Mensual",
  "paid_at": "2024-01-15T10:30:15Z"
}
```

---

## Mejores Prácticas

### Para Desarrolladores

- Usar transacciones para garantizar consistencia
- Validar webhooks para evitar fraude
- Registrar logs de todos los eventos de pago
- Implementar reintentos para pagos fallidos

### Para Administradores

- Monitorear tasa de éxito de pagos
- Investigar pagos fallidos recurrentes
- Procesar reembolsos de manera oportuna
- Mantener registros para auditorías

### Para Clientes

- Guardar comprobantes de pago
- Verificar cargos en estado de cuenta
- Reportar cargos no reconocidos
- Mantener métodos de pago actualizados
