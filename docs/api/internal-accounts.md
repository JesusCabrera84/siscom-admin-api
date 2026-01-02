# API Interna - Gestión de Accounts

## Descripción

La API interna de accounts proporciona listados y estadísticas globales del sistema para paneles administrativos.

> **Rol**: Dashboard administrativo con métricas y listados globales del sistema.

**Base URL**: `/api/v1/internal/accounts`

---

## Propósito

Este endpoint está diseñado para:

| Función | Descripción |
|---------|-------------|
| **Dashboard Global** | Métricas para paneles administrativos |
| **Listado de Accounts** | Visualizar todos los accounts con estadísticas |
| **Monitoreo** | Visibilidad del estado general del sistema |
| **Reportes** | Datos para reportes ejecutivos |

### Lo que PUEDE hacer

- ✅ Listar todos los accounts con estadísticas
- ✅ Filtrar accounts por estado y buscar por nombre
- ✅ Obtener conteo total de accounts por estado
- ✅ Obtener conteo total de devices por estado
- ✅ Obtener conteo de devices instalados (asignados a unidades)
- ✅ Obtener conteo total de usuarios

### Lo que NO PUEDE hacer

- ❌ Exponerse públicamente
- ❌ Usarse desde aplicaciones cliente (móvil/web pública)
- ❌ Acceder sin token PASETO válido

---

## Autenticación

Estos endpoints requieren un **token PASETO** con:

| Campo | Valor Requerido |
|-------|-----------------|
| `service` | `"gac"` |
| `role` | `"NEXUS_ADMIN"` |

---

## ⚠️ Advertencia de Seguridad

> ### 🚨 NUNCA EXPONER ESTA API PÚBLICAMENTE 🚨
>
> Esta API proporciona acceso a métricas globales del sistema.
>
> **Medidas obligatorias:**
> 1. Proteger el endpoint con firewall
> 2. Solo permitir acceso desde IPs de servicios autorizados
> 3. Usar VPN o red privada para comunicación
> 4. Implementar API Gateway con políticas restrictivas

---

## Endpoints

### 1. Listar Todos los Accounts

**GET** `/api/v1/internal/accounts`

Lista todos los accounts del sistema con estadísticas de organizaciones y usuarios.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Query Parameters

| Parámetro | Tipo   | Requerido | Descripción |
|-----------|--------|-----------|-------------|
| `status`  | string | No | Filtrar por estado (ACTIVE, SUSPENDED, DELETED) |
| `search`  | string | No | Buscar por nombre (parcial, case-insensitive) |
| `limit`   | int    | No | Máximo de resultados (default: 50, max: 200) |
| `offset`  | int    | No | Offset para paginación (default: 0) |

#### Ejemplo de Request

```bash
# Listar todos los accounts activos
curl -X GET "https://api.example.com/api/v1/internal/accounts?status=ACTIVE&limit=20" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Buscar accounts por nombre
curl -X GET "https://api.example.com/api/v1/internal/accounts?search=transportes" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "account_name": "Transportes XYZ S.A. de C.V.",
    "billing_email": "facturacion@transportesxyz.com",
    "status": "ACTIVE",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-20T15:45:00",
    "owner_email": "admin@transportesxyz.com",
    "total_organizations": 3,
    "total_users": 25
  },
  {
    "id": "234e4567-e89b-12d3-a456-426614174001",
    "account_name": "Logística ABC",
    "billing_email": "admin@logisticaabc.com",
    "status": "ACTIVE",
    "created_at": "2024-01-10T08:00:00",
    "updated_at": "2024-01-10T08:00:00",
    "owner_email": "ceo@logisticaabc.com",
    "total_organizations": 1,
    "total_users": 5
  }
]
```

#### Descripción de Campos

| Campo | Descripción |
|-------|-------------|
| `id` | UUID único del account |
| `account_name` | Nombre comercial del account |
| `billing_email` | Email para facturación |
| `status` | Estado del account (ACTIVE, SUSPENDED, DELETED) |
| `created_at` | Fecha de creación |
| `updated_at` | Fecha de última actualización |
| `owner_email` | Email del usuario owner del account |
| `total_organizations` | Cantidad de organizaciones en el account |
| `total_users` | Total de usuarios en todas las organizaciones |

---

### 2. Obtener Account por ID

**GET** `/api/v1/internal/accounts/{account_id}`

Obtiene información detallada de un account específico.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `account_id` | UUID | ID del account |

#### Ejemplo de Request

```bash
curl -X GET "https://api.example.com/api/v1/internal/accounts/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_name": "Transportes XYZ S.A. de C.V.",
  "billing_email": "facturacion@transportesxyz.com",
  "status": "ACTIVE",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-20T15:45:00",
  "owner_email": "admin@transportesxyz.com",
  "total_organizations": 3,
  "total_users": 25
}
```

#### Response 404 Not Found

```json
{
  "detail": "Account no encontrado"
}
```

---

### 3. Listar Organizaciones de un Account

**GET** `/api/v1/internal/accounts/{account_id}/organizations`

Lista todas las organizaciones de un account específico.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `account_id` | UUID | ID del account |

#### Ejemplo de Request

```bash
curl -X GET "https://api.example.com/api/v1/internal/accounts/123e4567-e89b-12d3-a456-426614174000/organizations" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
[
  {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Sucursal Norte",
    "status": "ACTIVE",
    "billing_email": "norte@transportesxyz.com",
    "country": "MX",
    "timezone": "America/Mexico_City",
    "total_users": 10,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-20T15:45:00"
  },
  {
    "id": "567e4567-e89b-12d3-a456-426614174001",
    "name": "Sucursal Sur",
    "status": "ACTIVE",
    "billing_email": "sur@transportesxyz.com",
    "country": "MX",
    "timezone": "America/Mexico_City",
    "total_users": 8,
    "created_at": "2024-02-01T09:00:00",
    "updated_at": "2024-02-01T09:00:00"
  }
]
```

#### Descripción de Campos

| Campo | Descripción |
|-------|-------------|
| `id` | UUID único de la organización |
| `name` | Nombre de la organización |
| `status` | Estado (PENDING, ACTIVE, SUSPENDED, DELETED) |
| `billing_email` | Email de facturación de la organización |
| `country` | País de la organización |
| `timezone` | Zona horaria |
| `total_users` | Cantidad de usuarios en la organización |
| `created_at` | Fecha de creación |
| `updated_at` | Fecha de última actualización |

#### Response 404 Not Found

```json
{
  "detail": "Account no encontrado"
}
```

---

### 4. Obtener Estadísticas Globales

**GET** `/api/v1/internal/accounts/stats`

Obtiene estadísticas globales del sistema incluyendo accounts, devices y usuarios.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Ejemplo de Request

```bash
curl -X GET "https://api.example.com/api/v1/internal/accounts/stats" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
{
  "accounts": {
    "total": 150,
    "by_status": {
      "active": 125,
      "suspended": 20,
      "deleted": 5
    }
  },
  "devices": {
    "total": 5000,
    "instalados": 3500,
    "by_status": {
      "nuevo": 200,
      "preparado": 150,
      "enviado": 100,
      "entregado": 300,
      "asignado": 3500,
      "devuelto": 250,
      "inactivo": 500
    }
  },
  "users": {
    "total": 450
  }
}
```

#### Descripción de Campos

##### Accounts

| Campo | Descripción |
|-------|-------------|
| `total` | Total de cuentas en el sistema |
| `by_status.active` | Cuentas activas |
| `by_status.suspended` | Cuentas suspendidas (falta de pago, violación TOS) |
| `by_status.deleted` | Cuentas eliminadas lógicamente |

##### Devices

| Campo | Descripción |
|-------|-------------|
| `total` | Total de dispositivos en el sistema |
| `instalados` | Dispositivos actualmente asignados a unidades |
| `by_status.nuevo` | Recién ingresados al inventario |
| `by_status.preparado` | Listos para envío |
| `by_status.enviado` | En tránsito al cliente |
| `by_status.entregado` | Recibidos por el cliente |
| `by_status.asignado` | Vinculados a una unidad (vehículo) |
| `by_status.devuelto` | Devueltos al inventario |
| `by_status.inactivo` | Fuera de uso o dados de baja |

##### Users

| Campo | Descripción |
|-------|-------------|
| `total` | Total de usuarios registrados en el sistema |

---

## Errores Comunes

### 401 Unauthorized

Token PASETO inválido, expirado o con permisos insuficientes.

```json
{
  "detail": "Token inválido. Se requiere un token PASETO de servicio válido."
}
```

**Soluciones:**
1. Verificar que el token no haya expirado
2. Generar un nuevo token con `POST /api/v1/auth/internal`
3. Asegurarse de usar `service: "gac"` y `role: "NEXUS_ADMIN"`

---

## Casos de Uso

### Listado de Accounts para Panel Admin

```javascript
// Obtener listado de accounts activos
const accounts = await fetch('/api/v1/internal/accounts?status=ACTIVE', {
  headers: { 'Authorization': `Bearer ${pasetoToken}` }
}).then(r => r.json());

// Mostrar en tabla
accounts.forEach(acc => {
  console.log(`${acc.account_name}: ${acc.total_organizations} orgs, ${acc.total_users} usuarios`);
});
```

### Dashboard Ejecutivo

```javascript
// Obtener métricas para dashboard
const stats = await fetch('/api/v1/internal/accounts/stats', {
  headers: { 'Authorization': `Bearer ${pasetoToken}` }
}).then(r => r.json());

// Mostrar KPIs
console.log(`Accounts activas: ${stats.accounts.by_status.active}`);
console.log(`Devices instalados: ${stats.devices.instalados} de ${stats.devices.total}`);
console.log(`Usuarios totales: ${stats.users.total}`);
```

### Monitoreo de Inventario

```javascript
// Calcular porcentaje de utilización de devices
const utilizacion = (stats.devices.instalados / stats.devices.total) * 100;
console.log(`Utilización de flota: ${utilizacion.toFixed(1)}%`);

// Alertar si hay muchos devices en estados intermedios
const enTransito = stats.devices.by_status.enviado + stats.devices.by_status.preparado;
if (enTransito > 100) {
  console.warn(`Alerta: ${enTransito} devices en tránsito`);
}
```

---

## Integración con gac-web

### Servicio de Cliente

```javascript
class InternalAccountsService {
  constructor(tokenManager) {
    this.tokenManager = tokenManager;
  }

  async listAccounts(params = {}) {
    const token = await this.tokenManager.getToken();
    const queryString = new URLSearchParams(params).toString();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/accounts?${queryString}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    return response.json();
  }

  async getStats() {
    const token = await this.tokenManager.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/accounts/stats`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    return response.json();
  }
}

export const internalAccountsService = new InternalAccountsService(tokenManager);
```

---

## Relación con Otros Endpoints

| Endpoint | Propósito |
|----------|-----------|
| `GET /internal/accounts` | Lista todos los accounts con estadísticas |
| `GET /internal/accounts/{id}` | Obtener un account específico |
| `GET /internal/accounts/{id}/organizations` | Listar organizaciones del account |
| `GET /internal/accounts/stats` | Estadísticas globales del sistema |
| `GET /internal/organizations` | Lista todas las organizaciones |
| `GET /internal/organizations/stats` | Estadísticas de organizaciones por estado |

---

**Última actualización**: Enero 2026  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)
