# API de Servicios de Dispositivos

## Descripción

Endpoints para gestionar servicios de rastreo por dispositivo. Los servicios representan la suscripción mensual o anual que activa el rastreo GPS de un dispositivo.

---

## Endpoints

### 1. Activar Servicio

**POST** `/api/v1/services/activate`

Activa un servicio de rastreo para un dispositivo específico.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "device_id": "123e4567-e89b-12d3-a456-426614174000",
  "plan_id": "223e4567-e89b-12d3-a456-426614174000",
  "subscription_type": "MONTHLY"
}
```

#### Validaciones

- El dispositivo debe pertenecer al cliente
- No puede existir otro servicio ACTIVE para el mismo dispositivo
- El plan debe existir y estar activo
- `subscription_type` debe ser `MONTHLY` o `YEARLY`

#### Response 201 Created

```json
{
  "id": "323e4567-e89b-12d3-a456-426614174000",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "device_id": "123e4567-e89b-12d3-a456-426614174000",
  "plan_id": "223e4567-e89b-12d3-a456-426614174000",
  "subscription_type": "MONTHLY",
  "status": "ACTIVE",
  "activated_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-02-14T10:30:00Z",
  "auto_renew": true,
  "payment_id": "abc12345-e89b-12d3-a456-426614174000"
}
```

#### Proceso Interno

1. Valida ownership del dispositivo
2. Verifica que no haya otro servicio ACTIVE
3. Crea registro de pago con estado `SUCCESS` (simulado)
4. Crea el servicio con estado `ACTIVE`
5. Calcula fecha de expiración automáticamente
6. Actualiza `device.active = true`

---

### 2. Listar Servicios Activos

**GET** `/api/v1/services/active`

Lista todos los servicios activos del cliente.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
[
  {
    "id": "323e4567-e89b-12d3-a456-426614174000",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "device_id": "123e4567-e89b-12d3-a456-426614174000",
    "plan_id": "223e4567-e89b-12d3-a456-426614174000",
    "subscription_type": "MONTHLY",
    "status": "ACTIVE",
    "activated_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-02-14T10:30:00Z",
    "auto_renew": true,
    "payment_id": "abc12345-e89b-12d3-a456-426614174000"
  }
]
```

---

### 3. Confirmar Pago de Servicio

**POST** `/api/v1/services/confirm-payment`

Confirma el pago de un servicio (usado cuando la activación no incluye pago inmediato).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "device_service_id": "323e4567-e89b-12d3-a456-426614174000",
  "payment_id": "abc12345-e89b-12d3-a456-426614174000"
}
```

#### Response 200 OK

```json
{
  "message": "Pago confirmado exitosamente",
  "device_service_id": "323e4567-e89b-12d3-a456-426614174000",
  "payment_id": "abc12345-e89b-12d3-a456-426614174000",
  "status": "ACTIVE"
}
```

---

### 4. Cancelar Servicio

**PATCH** `/api/v1/services/{service_id}/cancel`

Cancela un servicio activo.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `service_id`: UUID del servicio

#### Response 200 OK

```json
{
  "id": "323e4567-e89b-12d3-a456-426614174000",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "device_id": "123e4567-e89b-12d3-a456-426614174000",
  "plan_id": "223e4567-e89b-12d3-a456-426614174000",
  "subscription_type": "MONTHLY",
  "status": "CANCELLED",
  "activated_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-02-14T10:30:00Z",
  "cancelled_at": "2024-01-20T14:00:00Z",
  "auto_renew": false,
  "payment_id": "abc12345-e89b-12d3-a456-426614174000"
}
```

#### Proceso Interno

1. Valida que el servicio pertenezca al cliente
2. Actualiza el servicio a `CANCELLED`
3. Registra `cancelled_at`
4. Desactiva `auto_renew`
5. Actualiza `device.active = false`

---

## Estados del Servicio

### PENDING

- Servicio creado pero pago no confirmado
- Dispositivo aún no activo
- Esperando confirmación de pago

### ACTIVE

- Servicio pagado y activo
- Dispositivo enviando datos de rastreo
- Renovación automática si `auto_renew = true`

### EXPIRED

- Servicio expirado por tiempo
- No renovado automáticamente
- Dispositivo dejó de rastrear

### CANCELLED

- Servicio cancelado manualmente
- Puede ser antes de expiración natural
- Dispositivo desactivado

---

## Tipos de Suscripción

### MONTHLY

- Duración: 30 días
- Renovación mensual
- Precio según plan seleccionado

### YEARLY

- Duración: 365 días
- Renovación anual
- Generalmente con descuento vs mensual

---

## Cálculo de Fechas

### Fecha de Activación

```
activated_at = NOW()
```

### Fecha de Expiración

```
MONTHLY: expires_at = activated_at + 30 días
YEARLY:  expires_at = activated_at + 365 días
```

### Ejemplo

```
Activado: 2024-01-15 10:30:00
MONTHLY:  Expira: 2024-02-14 10:30:00
YEARLY:   Expira: 2025-01-15 10:30:00
```

---

## Restricción: Un Servicio Activo por Dispositivo

Existe un índice único parcial en la base de datos:

```sql
CREATE UNIQUE INDEX uq_device_services_active_one 
ON device_services(device_id) 
WHERE status = 'ACTIVE';
```

Esto garantiza que:
- Solo puede haber UN servicio ACTIVE por dispositivo
- No es posible tener dos suscripciones activas simultáneamente
- Histórico de servicios se mantiene (EXPIRED, CANCELLED)

---

## Renovación Automática

### Campo `auto_renew`

- **`true`**: El servicio se renovará automáticamente al expirar
- **`false`**: El servicio expirará sin renovarse

### Proceso de Renovación (TODO)

```
Servicio ACTIVE → expires_at alcanzado
                ↓
  auto_renew = true?
                ↓ Sí
  Crear nuevo pago
                ↓
  Crear nuevo servicio ACTIVE
                ↓
  Servicio anterior → EXPIRED
```

**Nota**: La renovación automática requiere integración con gateway de pagos.

---

## Relación con Pagos

Cada servicio está asociado a un pago:

```
DeviceService → Payment
  - payment_id (UUID)
  - payment.status: PENDING | SUCCESS | FAILED
  - payment.amount: precio del plan
```

### Flujo de Pago

```
1. Activar servicio → Crea Payment (PENDING o SUCCESS)
2. Payment SUCCESS → Servicio ACTIVE
3. Payment FAILED → Servicio PENDING (no activo)
```

---

## Relación con Planes

Cada servicio usa un plan específico:

```
DeviceService → Plan
  - plan_id (UUID)
  - plan.name: "Plan Básico", "Plan Premium", etc.
  - plan.monthly_price: precio mensual
  - plan.yearly_price: precio anual
```

---

## Consultas Útiles

### Servicios por Expirar (próximos 7 días)

```sql
SELECT * FROM device_services 
WHERE status = 'ACTIVE' 
  AND client_id = '...'
  AND expires_at <= NOW() + INTERVAL '7 days'
ORDER BY expires_at ASC;
```

### Servicios Expirados sin Renovar

```sql
SELECT * FROM device_services 
WHERE status = 'ACTIVE' 
  AND expires_at < NOW()
  AND auto_renew = false;
```

### Historial de Servicio de un Dispositivo

```sql
SELECT * FROM device_services 
WHERE device_id = '...'
ORDER BY activated_at DESC;
```

---

## Consideraciones de Negocio

### Facturación

- Cada activación genera un pago
- El monto se toma del plan seleccionado
- `payment.description` incluye detalles del servicio

### Métricas Importantes

- **MRR** (Monthly Recurring Revenue): Suma de servicios MONTHLY activos
- **ARR** (Annual Recurring Revenue): Suma de servicios YEARLY activos
- **Churn Rate**: Servicios cancelados vs total
- **Renewal Rate**: Servicios renovados vs expirados

### Recomendaciones

- Notificar al cliente 7 días antes de expiración
- Ofrecer renovación manual si `auto_renew = false`
- Enviar recordatorios de pago pendiente
- Implementar período de gracia (1-3 días) antes de desactivar

---

## Integración con Dispositivos

### Actualización Automática del Estado

```python
# Al activar servicio
device.active = True

# Al cancelar último servicio activo
if not device.tiene_otro_servicio_activo():
    device.active = False
```

### Validación de Dispositivo Activo

```python
def puede_enviar_datos(device):
    return device.active and device.tiene_servicio_activo()
```

---

## Errores Comunes

### 400 Bad Request: Servicio ya activo

```json
{
  "detail": "El dispositivo ya tiene un servicio activo"
}
```

**Solución**: Cancelar el servicio actual antes de activar uno nuevo.

### 404 Not Found: Dispositivo no encontrado

```json
{
  "detail": "Dispositivo no encontrado o no pertenece al cliente"
}
```

**Solución**: Verificar que el `device_id` sea correcto y pertenezca al cliente.

### 404 Not Found: Plan no encontrado

```json
{
  "detail": "Plan no encontrado"
}
```

**Solución**: Usar un `plan_id` válido de la lista de planes.

---

## Ejemplo Completo de Uso

### 1. Listar Planes Disponibles

```bash
GET /api/v1/plans/
```

### 2. Seleccionar Plan y Activar Servicio

```bash
POST /api/v1/services/activate
{
  "device_id": "...",
  "plan_id": "...",
  "subscription_type": "MONTHLY"
}
```

### 3. Verificar Servicios Activos

```bash
GET /api/v1/services/active
```

### 4. Cancelar Servicio si es Necesario

```bash
PATCH /api/v1/services/{service_id}/cancel
```

