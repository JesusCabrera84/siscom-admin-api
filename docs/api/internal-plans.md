# API Internal de Planes

## Descripción

Endpoints para la gestión completa de **Planes**, **Products** y **Capabilities**.

> **Uso exclusivo**: GAC (staff) con autenticación PASETO (`service=gac`)

Esta API soporta **operaciones compuestas** que permiten crear o editar un plan con todas sus dependencias en una sola llamada.

---

## Separación de APIs

### API Pública (`/api/v1/plans`)
- Uso por frontend cliente
- **Solo lectura**
- Solo muestra planes activos
- Orientada a UX (precios, features destacados)
- Ver: [API de Planes (Pública)](plans.md)

### API Internal (`/api/v1/internal/plans`)
- Uso exclusivo GAC (staff)
- Control total del catálogo
- Operaciones compuestas (crear/editar plan completo)
- Incluye planes activos e inactivos

---

## Índice de Endpoints

### Planes (Operaciones Compuestas)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/internal/plans` | Listar todos los planes |
| `POST` | `/internal/plans` | **Crear plan completo** |
| `GET` | `/internal/plans/{plan_id}` | Obtener plan |
| `PATCH` | `/internal/plans/{plan_id}` | **Actualizar plan completo** |
| `DELETE` | `/internal/plans/{plan_id}` | Eliminar plan |

### Capabilities de Plan (Uso avanzado)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/internal/plans/{plan_id}/capabilities` | Listar capabilities |
| `POST` | `/internal/plans/{plan_id}/capabilities/{code}` | Agregar capability |
| `DELETE` | `/internal/plans/{plan_id}/capabilities/{code}` | Eliminar capability |

### Productos de Plan (Uso avanzado)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/internal/plans/{plan_id}/products` | Listar productos |
| `POST` | `/internal/plans/{plan_id}/products/{code}` | Agregar producto |
| `DELETE` | `/internal/plans/{plan_id}/products/{code}` | Eliminar producto |

### Catálogo de Productos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/internal/plans/products` | Listar productos |
| `POST` | `/internal/plans/products` | Crear producto |
| `GET` | `/internal/plans/products/{product_id}` | Obtener producto |
| `PATCH` | `/internal/plans/products/{product_id}` | Actualizar producto |
| `DELETE` | `/internal/plans/products/{product_id}` | Eliminar producto |

### Catálogo de Capabilities (Read-only)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/internal/plans/capabilities` | Listar capabilities disponibles |

---

## Modelo de Datos

### Plan

```
plans
├── id (uuid, PK)
├── name (text, unique)
├── code (text, unique)
├── description (text)
├── price_monthly (numeric)
├── price_yearly (numeric)
├── is_active (bool, default: true)  ← NUEVO
├── created_at
└── updated_at
```

### Product

```
products
├── id (uuid, PK)
├── code (text, unique)
├── name (text)
├── description (text)
├── is_active (bool)
└── created_at
```

### Relaciones

```
Plan (1) ──< PlanCapability (N) >── Capability (1)
Plan (1) ──< PlanProduct (N) >── Product (1)
```

---

## Endpoints Principales (Compuestos)

### 1. Crear Plan Completo

**POST** `/api/v1/internal/plans`

Crea un plan con toda su configuración en **una sola operación atómica**:
- Datos comerciales (nombre, código, descripción)
- Precios
- Estado (activo/inactivo)
- Capabilities base
- Productos asociados

#### Headers

```
Authorization: Bearer <paseto_token>
Content-Type: application/json
```

#### Request Body

```json
{
  "name": "Plan Enterprise",
  "code": "enterprise",
  "description": "Plan para flotas grandes con funciones avanzadas",
  "price_monthly": "1499.00",
  "price_yearly": "14990.00",
  "is_active": true,
  "capabilities": [
    {"capability_code": "max_devices", "value_int": 500},
    {"capability_code": "max_users", "value_int": 100},
    {"capability_code": "ai_features", "value_bool": true},
    {"capability_code": "api_access", "value_bool": true}
  ],
  "product_codes": ["gps_tracker", "dashcam", "fuel_sensor"]
}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `name` | string | ✅ | Nombre del plan (único) |
| `code` | string | ✅ | Código del plan (único, minúsculas) |
| `description` | string | ❌ | Descripción del plan |
| `price_monthly` | decimal | ✅ | Precio mensual |
| `price_yearly` | decimal | ✅ | Precio anual |
| `is_active` | bool | ❌ | Si está activo (default: true) |
| `capabilities` | array | ❌ | Capabilities a incluir |
| `product_codes` | array | ❌ | Códigos de productos a incluir |

#### Response 201 Created

```json
{
  "id": "new-plan-uuid",
  "name": "Plan Enterprise",
  "code": "enterprise",
  "description": "Plan para flotas grandes con funciones avanzadas",
  "price_monthly": "1499.00",
  "price_yearly": "14990.00",
  "is_active": true,
  "capabilities": [
    {
      "capability_id": "cap-uuid",
      "capability_code": "max_devices",
      "value": 500,
      "value_type": "int"
    }
  ],
  "products": [
    {
      "product_id": "prod-uuid",
      "code": "gps_tracker",
      "name": "GPS Tracker Premium"
    }
  ],
  "subscriptions_count": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 404 | Capability 'xxx' no encontrada |
| 404 | Producto 'xxx' no encontrado |
| 409 | Ya existe un plan con código 'xxx' |
| 409 | Ya existe un plan con nombre 'xxx' |

---

### 2. Actualizar Plan Completo

**PATCH** `/api/v1/internal/plans/{plan_id}`

Actualiza un plan con **edición parcial**:
- Solo se actualizan los campos enviados
- Si se envían `capabilities`, se **reemplazan todas**
- Si se envían `product_codes`, se **reemplazan todos**

#### Request Body

```json
{
  "description": "Plan enterprise actualizado",
  "price_monthly": "1599.00",
  "price_yearly": "15990.00",
  "is_active": true,
  "capabilities": [
    {"capability_code": "max_devices", "value_int": 750},
    {"capability_code": "ai_features", "value_bool": true}
  ],
  "product_codes": ["gps_tracker", "dashcam", "fuel_sensor", "temperature_sensor"]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | string | Nuevo nombre (único) |
| `description` | string | Nueva descripción |
| `price_monthly` | decimal | Nuevo precio mensual |
| `price_yearly` | decimal | Nuevo precio anual |
| `is_active` | bool | Activar/desactivar plan |
| `capabilities` | array | **Reemplaza todas** las capabilities |
| `product_codes` | array | **Reemplaza todos** los productos |

#### Response 200 OK

Plan actualizado (misma estructura que creación).

---

### 3. Listar Planes

**GET** `/api/v1/internal/plans`

Lista todos los planes con información administrativa completa.

#### Query Parameters

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `include_inactive` | bool | `true` | Incluir planes inactivos |

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Plan Profesional",
    "code": "pro",
    "description": "Plan profesional para flotas medianas",
    "price_monthly": "599.00",
    "price_yearly": "5990.00",
    "is_active": true,
    "capabilities": [...],
    "products": [...],
    "subscriptions_count": 15,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### 4. Obtener Plan

**GET** `/api/v1/internal/plans/{plan_id}`

Obtiene un plan específico con toda su información.

---

### 5. Eliminar Plan

**DELETE** `/api/v1/internal/plans/{plan_id}`

Elimina un plan del sistema.

> **Restricción**: No se puede eliminar si tiene suscripciones activas.  
> **Recomendación**: Desactivar (`is_active: false`) en lugar de eliminar.

#### Response 204 No Content

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 400 | No se puede eliminar: tiene N suscripciones activas |
| 404 | Plan no encontrado |

---

## Endpoints Auxiliares (Uso Avanzado)

> **Nota**: Para la UI principal de creación/edición, usar los endpoints compuestos.  
> Estos endpoints son para ajustes puntuales o automatizaciones.

### Capabilities de Plan

#### Listar Capabilities

**GET** `/api/v1/internal/plans/{plan_id}/capabilities`

```json
{
  "plan_id": "plan-uuid",
  "plan_code": "pro",
  "capabilities": [
    {
      "plan_id": "plan-uuid",
      "capability_id": "cap-uuid",
      "capability_code": "max_devices",
      "value": 50,
      "value_type": "int",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### Agregar Capability

**POST** `/api/v1/internal/plans/{plan_id}/capabilities/{capability_code}`

```json
{
  "capability_code": "max_devices",
  "value_int": 100
}
```

#### Eliminar Capability

**DELETE** `/api/v1/internal/plans/{plan_id}/capabilities/{capability_code}`

---

### Productos de Plan

#### Listar Productos

**GET** `/api/v1/internal/plans/{plan_id}/products`

#### Agregar Producto

**POST** `/api/v1/internal/plans/{plan_id}/products/{product_code}`

#### Eliminar Producto

**DELETE** `/api/v1/internal/plans/{plan_id}/products/{product_code}`

---

## Catálogo de Productos

### Listar Productos

**GET** `/api/v1/internal/plans/products`

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `include_inactive` | bool | `false` | Incluir productos inactivos |

### Crear Producto

**POST** `/api/v1/internal/plans/products`

```json
{
  "code": "fuel_sensor",
  "name": "Sensor de Combustible",
  "description": "Sensor para monitoreo de nivel de combustible",
  "is_active": true
}
```

### Actualizar Producto

**PATCH** `/api/v1/internal/plans/products/{product_id}`

### Eliminar Producto

**DELETE** `/api/v1/internal/plans/products/{product_id}`

> No se puede eliminar si está asociado a planes.

---

## Catálogo de Capabilities

### Listar Capabilities Disponibles

**GET** `/api/v1/internal/plans/capabilities`

Lista todas las capabilities del sistema (read-only).

```json
[
  {
    "id": "cap-uuid",
    "code": "max_devices",
    "description": "Número máximo de dispositivos",
    "value_type": "int"
  },
  {
    "id": "cap-uuid-2",
    "code": "ai_features",
    "description": "Acceso a funciones de IA",
    "value_type": "bool"
  }
]
```

---

## Ejemplos con cURL

### Crear Plan Completo (Una sola llamada)

```bash
curl -X POST "http://localhost:8000/api/v1/internal/plans" \
  -H "Authorization: Bearer <paseto_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Plan Profesional",
    "code": "pro",
    "description": "Para flotas medianas",
    "price_monthly": "599.00",
    "price_yearly": "5990.00",
    "is_active": true,
    "capabilities": [
      {"capability_code": "max_devices", "value_int": 50},
      {"capability_code": "max_users", "value_int": 10},
      {"capability_code": "ai_features", "value_bool": true}
    ],
    "product_codes": ["gps_tracker"]
  }'
```

### Actualizar Plan Completo (Una sola llamada)

```bash
curl -X PATCH "http://localhost:8000/api/v1/internal/plans/{plan_id}" \
  -H "Authorization: Bearer <paseto_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_monthly": "649.00",
    "price_yearly": "6490.00",
    "capabilities": [
      {"capability_code": "max_devices", "value_int": 75},
      {"capability_code": "ai_features", "value_bool": true}
    ]
  }'
```

### Desactivar Plan

```bash
curl -X PATCH "http://localhost:8000/api/v1/internal/plans/{plan_id}" \
  -H "Authorization: Bearer <paseto_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

## Reglas de Negocio

1. **Una sola llamada**: La UI de GAC crea/edita planes completos en una operación
2. **Operaciones atómicas**: Si falla alguna parte, se hace rollback completo
3. **Reemplazo de relaciones**: Al enviar `capabilities` o `product_codes`, se reemplazan todos
4. **Edición parcial**: Solo se actualizan los campos enviados
5. **Códigos únicos**: Planes y productos tienen códigos únicos (minúsculas, números, guión bajo)
6. **No eliminar planes activos**: Preferir desactivar (`is_active: false`)
7. **Capabilities predefinidas**: Deben existir en la tabla `capabilities`

---

## Notas Importantes

- Los planes inactivos no aparecen en la API pública
- Los planes con suscripciones activas no pueden eliminarse
- Los productos asociados a planes no pueden eliminarse
- Las capabilities deben existir previamente en el sistema
- El frontend no debe conocer la estructura interna de relaciones

---

**Última actualización**: Enero 2026  
**Autenticación requerida**: PASETO (service=gac)

