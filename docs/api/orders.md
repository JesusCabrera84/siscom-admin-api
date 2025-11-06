# API de Órdenes

## Descripción

Endpoints para gestionar órdenes de compra de dispositivos GPS. Las órdenes representan la compra física de hardware.

---

## Endpoints

### 1. Crear Orden

**POST** `/api/v1/orders/`

Crea una nueva orden de compra con uno o más dispositivos.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "items": [
    {
      "device_serial": "GPS-2024-001",
      "device_model": "TK103",
      "device_imei": "353451234567890",
      "unit_price": 1500.00,
      "quantity": 2
    },
    {
      "device_serial": "GPS-2024-002",
      "device_model": "TK303",
      "device_imei": "353451234567891",
      "unit_price": 2000.00,
      "quantity": 1
    }
  ]
}
```

#### Response 201 Created

```json
{
  "id": "789e4567-e89b-12d3-a456-426614174000",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "status": "PENDING",
  "total_amount": 5000.00,
  "items": [
    {
      "id": "item-1",
      "order_id": "789e4567-e89b-12d3-a456-426614174000",
      "device_serial": "GPS-2024-001",
      "device_model": "TK103",
      "device_imei": "353451234567890",
      "unit_price": 1500.00,
      "quantity": 2,
      "subtotal": 3000.00
    },
    {
      "id": "item-2",
      "order_id": "789e4567-e89b-12d3-a456-426614174000",
      "device_serial": "GPS-2024-002",
      "device_model": "TK303",
      "device_imei": "353451234567891",
      "unit_price": 2000.00,
      "quantity": 1,
      "subtotal": 2000.00
    }
  ],
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 2. Listar Órdenes

**GET** `/api/v1/orders/`

Lista todas las órdenes del cliente autenticado.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
[
  {
    "id": "789e4567-e89b-12d3-a456-426614174000",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "status": "COMPLETED",
    "total_amount": 5000.00,
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T14:00:00Z"
  }
]
```

---

### 3. Obtener Detalle de Orden

**GET** `/api/v1/orders/{order_id}`

Obtiene el detalle completo de una orden específica, incluyendo sus items.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `order_id`: UUID de la orden

#### Response 200 OK

```json
{
  "id": "789e4567-e89b-12d3-a456-426614174000",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "status": "COMPLETED",
  "total_amount": 5000.00,
  "items": [
    {
      "id": "item-1",
      "device_serial": "GPS-2024-001",
      "device_model": "TK103",
      "unit_price": 1500.00,
      "quantity": 2,
      "subtotal": 3000.00
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T14:00:00Z"
}
```

---

## Estados de la Orden

### PENDING

- Orden creada, esperando pago
- Dispositivos reservados pero no creados
- Cliente puede cancelar

### PAID

- Pago confirmado
- Dispositivos aún no enviados/entregados
- En proceso de cumplimiento

### COMPLETED

- Orden completada
- Dispositivos entregados al cliente
- Dispositivos creados en el sistema

### CANCELLED

- Orden cancelada
- Pago reembolsado (si aplica)
- Dispositivos liberados

---

## Cálculo del Total

```
total_amount = SUM(item.unit_price * item.quantity)

Ejemplo:
Item 1: $1,500 * 2 = $3,000
Item 2: $2,000 * 1 = $2,000
Total:              $5,000
```

---

## Relación con Dispositivos

Al completar una orden, se crean los dispositivos automáticamente:

```
Orden COMPLETED → Crea dispositivos en BD
                ↓
  Por cada item:
    - device_serial
    - device_model
    - device_imei
                ↓
  Dispositivos listos para instalación
```

---

## Relación con Pagos

Cada orden genera un pago asociado:

```
Order → Payment
  - payment.order_id = order.id
  - payment.amount = order.total_amount
  - payment.description = "Orden #[order_id]"
```

---

## Flujo Completo de Compra

### 1. Cliente Crea Orden

```bash
POST /api/v1/orders/
{
  "items": [...]
}
```

### 2. Sistema Crea Orden PENDING

```
Order.status = PENDING
Order.total_amount = calculado
Payment.status = PENDING
```

### 3. Cliente Realiza Pago

```
Integración con gateway de pago
(Stripe, MercadoPago, etc.)
```

### 4. Webhook de Pago Confirmado

```
Payment.status = SUCCESS
Order.status = PAID
```

### 5. Orden Cumplida (Envío)

```
Dispositivos enviados físicamente
Order.status = COMPLETED
Dispositivos creados en BD
```

---

## Validaciones

### Al Crear Orden

- Debe incluir al menos un item
- Cada item debe tener `unit_price > 0`
- Cada item debe tener `quantity > 0`
- `device_serial` debe ser único
- `device_imei` debe ser único y tener 15 dígitos

### Al Cancelar Orden

- Solo órdenes `PENDING` o `PAID` pueden cancelarse
- Órdenes `COMPLETED` no pueden cancelarse
- Se debe procesar reembolso si aplica

---

## Items de la Orden

Cada item representa un tipo de dispositivo:

```json
{
  "device_serial": "GPS-2024-001",  // Número de serie del dispositivo
  "device_model": "TK103",          // Modelo del hardware
  "device_id": "353451234567890",   // Device ID único del dispositivo
  "unit_price": 1500.00,            // Precio unitario
  "quantity": 2,                    // Cantidad de dispositivos
  "subtotal": 3000.00               // unit_price * quantity
}
```

---

## Consideraciones de Negocio

### Inventario

- El sistema NO gestiona inventario automáticamente
- Las órdenes se crean bajo demanda
- Validar disponibilidad manualmente antes de confirmar

### Facturación

- Cada orden genera una factura
- El `total_amount` es el monto a facturar
- Incluir IVA según regulaciones locales

### Envío

- Coordinar envío físico fuera del sistema
- Actualizar estado a `COMPLETED` al entregar
- Notificar al cliente sobre estado de envío

---

## Ejemplo Completo

### 1. Cliente Consulta Precios

```
Contacto con ventas para cotización
```

### 2. Cliente Crea Orden

```bash
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "device_serial": "GPS-2024-001",
        "device_model": "TK103",
        "device_imei": "353451234567890",
        "unit_price": 1500.00,
        "quantity": 2
      }
    ]
  }'
```

### 3. Cliente Recibe Orden PENDING

```json
{
  "id": "...",
  "status": "PENDING",
  "total_amount": 3000.00
}
```

### 4. Cliente Paga (Fuera del Sistema)

```
Transferencia, tarjeta, etc.
```

### 5. Admin Confirma Pago

```sql
UPDATE payments 
SET status = 'SUCCESS' 
WHERE order_id = '...';

UPDATE orders 
SET status = 'PAID' 
WHERE id = '...';
```

### 6. Admin Envía Dispositivos

```
Envío físico con paquetería
```

### 7. Admin Marca Orden como COMPLETED

```sql
UPDATE orders 
SET status = 'COMPLETED', 
    completed_at = NOW() 
WHERE id = '...';

-- Crear dispositivos en BD
INSERT INTO devices (...)
VALUES (...);
```

### 8. Cliente Recibe Dispositivos

```
Cliente instala dispositivos en vehículos
Cliente activa servicios de rastreo
```

---

## Mejores Prácticas

### Para Desarrolladores

- Validar unicidad de seriales e IMEIs antes de crear orden
- Usar transacciones para garantizar consistencia
- Registrar logs de cambios de estado

### Para Administradores

- Confirmar disponibilidad antes de aprobar órdenes
- Actualizar estados de manera oportuna
- Mantener comunicación con cliente sobre envíos

### Para Clientes

- Verificar información de dispositivos antes de ordenar
- Guardar número de orden para seguimiento
- Confirmar recepción de dispositivos

