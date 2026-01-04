# API Interna - Gestión de Productos

## Descripción

Endpoints para la gestión completa de **Productos** del catálogo.

> **Uso exclusivo**: GAC (staff) con autenticación PASETO (`service=gac`)

Esta API permite gestionar el catálogo de productos que pueden incluirse en planes de suscripción.

**Base URL**: `/api/v1/internal/products`

---

## Propósito

Este endpoint está diseñado para:

| Función | Descripción |
|---------|-------------|
| **Catálogo de Productos** | Gestión completa del catálogo de productos disponibles |
| **CRUD Completo** | Crear, leer, actualizar y desactivar productos |
| **Integración con Planes** | Productos que se pueden asociar a planes de suscripción |
| **Soft Delete** | Desactivación lógica (no eliminación física) |

### Lo que PUEDE hacer

- ✅ Listar todos los productos con filtros y búsqueda
- ✅ Crear nuevos productos con validación de unicidad
- ✅ Obtener producto específico por ID
- ✅ Actualizar productos parcialmente
- ✅ Desactivar productos (soft delete - solo cambia `is_active`)

### Lo que NO PUEDE hacer

- ❌ Exponerse públicamente
- ❌ Usarse desde aplicaciones cliente (móvil/web pública)
- ❌ Acceder sin token PASETO válido
- ❌ Eliminar productos físicamente de la base de datos

---

## Autenticación

Estos endpoints requieren un **token PASETO** con:

| Campo | Valor Requerido |
|-------|-----------------|
| `service` | `"gac"` |
| `role` | `"GAC_ADMIN"` |

---

## ⚠️ Advertencia de Seguridad

> ### 🚨 NUNCA EXPONER ESTA API PÚBLICAMENTE 🚨
>
> Esta API proporciona acceso completo al catálogo de productos.
>
> **Medidas obligatorias:**
> 1. Proteger el endpoint con firewall
> 2. Solo permitir acceso desde IPs de servicios autorizados
> 3. Usar VPN o red privada para comunicación
> 4. Implementar API Gateway con políticas restrictivas

---

## Índice de Endpoints

### Gestión de Productos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/internal/products` | Listar todos los productos |
| `POST` | `/internal/products` | Crear un nuevo producto |
| `GET` | `/internal/products/{product_id}` | Obtener producto específico |
| `PATCH` | `/internal/products/{product_id}` | Actualizar producto |
| `DELETE` | `/internal/products/{product_id}` | Desactivar producto (soft delete) |

---

## Modelo de Datos

### Product

```
products
├── id (uuid, PK, gen_random_uuid())
├── code (text, unique, not null)        ← Código único (ej: gps_tracker)
├── name (text, not null)                ← Nombre del producto
├── description (text, nullable)         ← Descripción opcional
├── is_active (bool, default: true)      ← Estado del producto
└── created_at (timestamptz, default: now())
```

### Restricciones

- `code`: Debe ser único, solo letras minúsculas, números y guiones bajos
- `name`: Obligatorio, máximo 255 caracteres
- `description`: Opcional, sin límite de caracteres
- `DELETE`: Solo cambia `is_active = false` (soft delete)

---

## Endpoints

### 1. Listar Todos los Productos

**GET** `/api/v1/internal/products`

Lista todos los productos del catálogo con soporte para filtros y paginación.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Query Parameters

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `search` | string | No | Buscar por código o nombre (parcial, case-insensitive) |
| `is_active` | boolean | No | Filtrar por estado activo (`true`/`false`) |
| `limit` | int | No | Máximo de resultados (default: 50, max: 200) |
| `offset` | int | No | Offset para paginación (default: 0) |

#### Response (200 OK)

```json
{
  "products": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "code": "gps_tracker",
      "name": "GPS Tracker Premium",
      "description": "Dispositivo GPS con rastreo en tiempo real",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### Ejemplos de Request

```bash
# Listar todos los productos activos
curl -X GET "https://api.example.com/api/v1/internal/products?is_active=true&limit=20" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Buscar productos por nombre
curl -X GET "https://api.example.com/api/v1/internal/products?search=gps" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Listar productos inactivos con paginación
curl -X GET "https://api.example.com/api/v1/internal/products?is_active=false&limit=10&offset=20" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

---

### 2. Crear un Nuevo Producto

**POST** `/api/v1/internal/products`

Crea un nuevo producto en el catálogo.

#### Headers

```
Authorization: Bearer <token_paseto>
Content-Type: application/json
```

#### Request Body

```json
{
  "code": "gps_tracker",
  "name": "GPS Tracker Premium",
  "description": "Dispositivo GPS con rastreo en tiempo real",
  "is_active": true
}
```

#### Campos Requeridos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `code` | string | Código único (3-50 chars, solo `a-z0-9_`) |
| `name` | string | Nombre del producto (1-255 chars) |

#### Campos Opcionales

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `description` | string | `null` | Descripción detallada |
| `is_active` | boolean | `true` | Estado inicial del producto |

#### Response (201 Created)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "code": "gps_tracker",
  "name": "GPS Tracker Premium",
  "description": "Dispositivo GPS con rastreo en tiempo real",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Ejemplo de Request

```bash
curl -X POST "https://api.example.com/api/v1/internal/products" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..." \
  -H "Content-Type: application/json" \
  -d '{
    "code": "dashcam_hd",
    "name": "Dashcam HD 1080p",
    "description": "Cámara de tablero con grabación en alta definición",
    "is_active": true
  }'
```

#### Errores Comunes

- **409 Conflict**: Código ya existe (`"code": "El código 'gps_tracker' ya existe"`)
- **422 Unprocessable Entity**: Validación fallida (código inválido, campos requeridos faltantes)

---

### 3. Obtener Producto Específico

**GET** `/api/v1/internal/products/{product_id}`

Obtiene los detalles de un producto específico por su ID.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `product_id` | UUID | ID único del producto |

#### Response (200 OK)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "code": "gps_tracker",
  "name": "GPS Tracker Premium",
  "description": "Dispositivo GPS con rastreo en tiempo real",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Ejemplo de Request

```bash
curl -X GET "https://api.example.com/api/v1/internal/products/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Errores

- **404 Not Found**: Producto no encontrado (`"detail": "Producto con ID 'uuid' no encontrado"`)

---

### 4. Actualizar Producto

**PATCH** `/api/v1/internal/products/{product_id}`

Actualiza parcialmente un producto existente. Solo se actualizan los campos enviados.

#### Headers

```
Authorization: Bearer <token_paseto>
Content-Type: application/json
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `product_id` | UUID | ID único del producto |

#### Request Body (parcial)

```json
{
  "name": "GPS Tracker Premium v2",
  "description": "Dispositivo GPS mejorado con nuevas características",
  "is_active": true
}
```

#### Campos Opcionales (al menos uno requerido)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | string | Nuevo nombre del producto |
| `description` | string | Nueva descripción |
| `is_active` | boolean | Nuevo estado del producto |

#### Response (200 OK)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "code": "gps_tracker",
  "name": "GPS Tracker Premium v2",
  "description": "Dispositivo GPS mejorado con nuevas características",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Ejemplo de Request

```bash
curl -X PATCH "https://api.example.com/api/v1/internal/products/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..." \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Versión mejorada con GPS dual y mayor precisión",
    "is_active": true
  }'
```

#### Errores

- **404 Not Found**: Producto no encontrado
- **422 Unprocessable Entity**: Campos inválidos

---

### 5. Desactivar Producto (Soft Delete)

**DELETE** `/api/v1/internal/products/{product_id}`

Desactiva un producto cambiando su estado `is_active` a `false`. **No elimina físicamente** el registro.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `product_id` | UUID | ID único del producto |

#### Response (204 No Content)

Sin contenido en el body.

#### Ejemplo de Request

```bash
curl -X DELETE "https://api.example.com/api/v1/internal/products/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Comportamiento

- El producto queda **inactivo** (`is_active = false`)
- El registro **no se elimina** de la base de datos
- El producto ya **no aparece** en listados por defecto
- Se puede **reactivar** cambiando `is_active = true` vía PATCH

#### Errores

- **404 Not Found**: Producto no encontrado
- **400 Bad Request**: Producto ya está desactivado (`"detail": "El producto ya está desactivado"`)

---

## Consideraciones de Uso

### Soft Delete

El endpoint `DELETE` implementa **soft delete** cambiando solo el campo `is_active` a `false`. Esto permite:

- Mantener integridad referencial con planes existentes
- Auditar cambios históricos
- Reactivar productos si es necesario
- Evitar pérdida accidental de datos

### Validación de Código

Los códigos de producto deben seguir el patrón `^[a-z0-9_]+$`:

- Solo letras minúsculas
- Números
- Guiones bajos
- Longitud: 1-50 caracteres

### Estados de Producto

- **`is_active = true`**: Producto disponible para nuevos planes
- **`is_active = false`**: Producto desactivado, no disponible para nuevos planes

### Paginación

La lista de productos soporta paginación estándar:

- `limit`: Máximo 200 productos por página
- `offset`: Para navegación entre páginas
- `total`: Conteo total en la respuesta

---

## Ejemplos de Flujo Completo

### Crear y Gestionar un Producto

```bash
# 1. Crear producto
curl -X POST "https://api.example.com/api/v1/internal/products" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..." \
  -H "Content-Type: application/json" \
  -d '{
    "code": "fuel_sensor",
    "name": "Sensor de Combustible Digital",
    "description": "Sensor capacitivo para medición precisa de nivel de combustible",
    "is_active": true
  }'

# 2. Obtener producto creado
curl -X GET "https://api.example.com/api/v1/internal/products/{product_id}" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# 3. Actualizar descripción
curl -X PATCH "https://api.example.com/api/v1/internal/products/{product_id}" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..." \
  -H "Content-Type: application/json" \
  -d '{"description": "Sensor mejorado con calibración automática"}'

# 4. Desactivar producto (si ya no se usa)
curl -X DELETE "https://api.example.com/api/v1/internal/products/{product_id}" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```
