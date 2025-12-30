# API de Suscripciones

## Descripción

Endpoints para gestionar las suscripciones de una organización. Una organización puede tener **múltiples suscripciones** activas e históricas.

> **Concepto Clave**: Las suscripciones activas se **calculan dinámicamente**, no se almacenan como un campo fijo. Ver [Modelo Organizacional](../guides/organizational-model.md).

> **Modelo v2**: Las suscripciones pertenecen a `organizations` (no a `accounts`). El campo `organization_id` es la FK.

---

## Principios Fundamentales

### Suscripciones Múltiples

Una organización puede tener varias suscripciones:

```
Organización "Transportes XYZ"
├── Suscripción 1 (ACTIVE, Plan Enterprise) ← Actual
├── Suscripción 2 (EXPIRED, Plan Pro)       ← Histórica
└── Suscripción 3 (CANCELLED, Plan Básico)  ← Histórica
```

### Cálculo de Suscripción Activa

**Regla Única de Suscripción Activa** (definida en `app/services/subscription_query.py`):

```
Una suscripción se considera ACTIVA si cumple TODAS las condiciones:
┌─────────────────────────────────────────────────────────────┐
│  1. status IN ('ACTIVE', 'TRIAL')                           │
│  2. expires_at > now() OR expires_at IS NULL                │
└─────────────────────────────────────────────────────────────┘
```

```python
# Enfoque CORRECTO - Usar módulo centralizado
from app.services.subscription_query import (
    get_active_subscriptions,        # Lista todas las activas
    get_primary_active_subscription, # La más reciente (para capabilities)
    has_active_subscription,         # Verificar si tiene alguna
)

# Todas las funciones usan organization_id como parámetro
get_active_subscriptions(db, organization_id)
```

#### Múltiples Suscripciones Activas

Si una organización tiene múltiples suscripciones activas:
- **Para capabilities:** Se usa la más reciente (`ORDER BY started_at DESC LIMIT 1`)
- **Para listados:** Se muestran todas ordenadas por `started_at DESC`

### Estados de Suscripción

| Estado | Descripción |
|--------|-------------|
| `ACTIVE` | Suscripción vigente y operativa |
| `TRIAL` | Período de prueba |
| `EXPIRED` | Venció por tiempo |
| `CANCELLED` | Cancelada manualmente |

---

## Endpoints

### 1. Listar Suscripciones

**GET** `/api/v1/subscriptions/`

Lista todas las suscripciones de la organización, incluyendo activas e históricas.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `include_history` | bool | `true` | Incluir suscripciones históricas |
| `limit` | int | `20` | Límite de resultados (máx 100) |

#### Response 200 OK

```json
{
  "subscriptions": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "organization_id": "456e4567-e89b-12d3-a456-426614174000",
      "plan_id": "789e4567-e89b-12d3-a456-426614174000",
      "plan_name": "Plan Enterprise",
      "plan_code": "enterprise",
      "status": "ACTIVE",
      "billing_cycle": "YEARLY",
      "started_at": "2024-01-01T00:00:00Z",
      "expires_at": "2025-01-01T00:00:00Z",
      "auto_renew": true,
      "days_remaining": 180,
      "is_active": true
    },
    {
      "id": "234e4567-e89b-12d3-a456-426614174001",
      "organization_id": "456e4567-e89b-12d3-a456-426614174000",
      "plan_id": "890e4567-e89b-12d3-a456-426614174000",
      "plan_name": "Plan Pro",
      "plan_code": "pro",
      "status": "EXPIRED",
      "billing_cycle": "MONTHLY",
      "started_at": "2023-01-01T00:00:00Z",
      "expires_at": "2024-01-01T00:00:00Z",
      "auto_renew": false,
      "days_remaining": null,
      "is_active": false
    }
  ],
  "active_count": 1,
  "total_count": 2
}
```

---

### 2. Listar Suscripciones Activas

**GET** `/api/v1/subscriptions/active`

Lista solo las suscripciones activas (status ACTIVE o TRIAL y no expiradas).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "plan_name": "Plan Enterprise",
    "plan_code": "enterprise",
    "status": "ACTIVE",
    "started_at": "2024-01-01T00:00:00Z",
    "expires_at": "2025-01-01T00:00:00Z",
    "auto_renew": true,
    "days_remaining": 180,
    "is_active": true
  }
]
```

---

### 3. Obtener Suscripción por ID

**GET** `/api/v1/subscriptions/{subscription_id}`

Obtiene los detalles completos de una suscripción específica.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "organization_id": "456e4567-e89b-12d3-a456-426614174000",
  "plan_id": "789e4567-e89b-12d3-a456-426614174000",
  "plan_name": "Plan Enterprise",
  "plan_code": "enterprise",
  "status": "ACTIVE",
  "billing_cycle": "YEARLY",
  "started_at": "2024-01-01T00:00:00Z",
  "expires_at": "2025-01-01T00:00:00Z",
  "cancelled_at": null,
  "renewed_from": null,
  "auto_renew": true,
  "external_id": "sub_stripe_1234567890",
  "current_period_start": "2024-06-01T00:00:00Z",
  "current_period_end": "2024-07-01T00:00:00Z",
  "days_remaining": 180,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-06-01T00:00:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 404 | `"Suscripción no encontrada"` |

---

### 4. Cancelar Suscripción

**POST** `/api/v1/subscriptions/{subscription_id}/cancel`

Cancela una suscripción activa.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Permisos Requeridos

- Rol: `owner`, `billing`

#### Request Body

```json
{
  "reason": "Ya no necesito el servicio",
  "cancel_immediately": false
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `reason` | string (opcional) | Razón de la cancelación |
| `cancel_immediately` | bool | Si `true`, cancela inmediatamente. Si `false`, cancela al final del período. |

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "CANCELLED",
  "cancelled_at": "2024-06-15T10:00:00Z",
  "auto_renew": false,
  "expires_at": "2025-01-01T00:00:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 403 | `"Se requiere uno de los siguientes roles: owner, billing"` |
| 404 | `"Suscripción no encontrada"` |
| 400 | `"La suscripción ya está cancelada"` |

---

### 5. Activar/Desactivar Renovación Automática

**PATCH** `/api/v1/subscriptions/{subscription_id}/auto-renew`

Activa o desactiva la renovación automática de una suscripción.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Permisos Requeridos

- Rol: `owner`, `billing`

#### Query Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `auto_renew` | bool | Nuevo valor de auto-renovación |

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "auto_renew": false
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 403 | `"Se requiere uno de los siguientes roles: owner, billing"` |
| 400 | `"Solo se puede modificar suscripciones activas"` |

---

## Ciclo de Vida de una Suscripción

```
┌─────────────────────────────────────────────────────────────────┐
│                 CICLO DE VIDA DE SUSCRIPCIÓN                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CREACIÓN                                                    │
│     POST /api/v1/services/activate                              │
│     status = ACTIVE o TRIAL                                     │
│                                                                 │
│  2. OPERACIÓN NORMAL                                            │
│     Usuario usa el servicio según capabilities del plan         │
│                                                                 │
│  3. RENOVACIÓN (si auto_renew = true)                          │
│     Sistema renueva automáticamente antes de expires_at        │
│     Nueva suscripción con renewed_from = suscripción anterior  │
│                                                                 │
│  4. CANCELACIÓN (opción A)                                      │
│     POST /api/v1/subscriptions/{id}/cancel                      │
│     cancel_immediately = false → mantiene hasta expires_at      │
│     cancel_immediately = true → termina inmediatamente          │
│                                                                 │
│  5. EXPIRACIÓN (opción B)                                       │
│     Sistema marca como EXPIRED cuando expires_at < now()        │
│     Si auto_renew = false, no se renueva                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Campos de la Suscripción

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único |
| `organization_id` | UUID | Organización propietaria |
| `plan_id` | UUID | Plan asociado |
| `status` | enum | Estado actual |
| `billing_cycle` | enum | MONTHLY o YEARLY |
| `started_at` | datetime | Fecha de inicio |
| `expires_at` | datetime | Fecha de expiración |
| `cancelled_at` | datetime | Fecha de cancelación (si aplica) |
| `renewed_from` | UUID | Suscripción de la que se renovó |
| `auto_renew` | bool | Si se renueva automáticamente |
| `external_id` | string | ID externo (ej: Stripe) |
| `current_period_start` | datetime | Inicio del período actual |
| `current_period_end` | datetime | Fin del período actual |

---

## Relación con Capabilities

Las suscripciones determinan las capabilities disponibles:

```
Suscripción ACTIVE
      ↓
  Plan asociado
      ↓
  plan_capabilities
      ↓
  (+ organization_overrides)
      ↓
  Capabilities Efectivas
```

Ver [API de Capabilities](capabilities.md) para más detalles.

---

## Ejemplos de Uso

### Consultar Suscripciones

```bash
curl -X GET http://localhost:8000/api/v1/subscriptions/ \
  -H "Authorization: Bearer <token>"
```

### Cancelar Suscripción al Final del Período

```bash
curl -X POST http://localhost:8000/api/v1/subscriptions/123e4567.../cancel \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Cambio de proveedor",
    "cancel_immediately": false
  }'
```

### Desactivar Renovación Automática

```bash
curl -X PATCH "http://localhost:8000/api/v1/subscriptions/123e4567.../auto-renew?auto_renew=false" \
  -H "Authorization: Bearer <token>"
```

---

**Última actualización**: Diciembre 2025  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)

