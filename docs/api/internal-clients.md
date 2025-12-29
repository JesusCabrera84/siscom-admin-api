# API Interna - Orquestador Administrativo

## Descripción

La API interna proporciona endpoints administrativos para gestión global del sistema. Funciona como un **orquestador administrativo** que permite operaciones cross-organization que no están disponibles para usuarios regulares.

> **Rol**: Panel de administración interno para operaciones que trascienden el contexto de una sola organización.

**Base URL**: `/api/v1/internal/clients`

---

## Propósito del Orquestador

La API interna está diseñada para:

| Función | Descripción |
|---------|-------------|
| **Administración Global** | Gestionar todas las organizaciones del sistema |
| **Operaciones Cross-Org** | Ejecutar acciones que afectan múltiples organizaciones |
| **Panel Administrativo** | Soporte para aplicaciones como **gac-web** |
| **Inspección** | Revisar estado de suscripciones y capabilities |
| **Control de Estado** | Suspender/reactivar organizaciones |

### Lo que PUEDE hacer

- ✅ Listar TODAS las organizaciones
- ✅ Cambiar estado de organizaciones (ACTIVE / SUSPENDED)
- ✅ Inspeccionar suscripciones de cualquier organización
- ✅ Ver capabilities efectivas de organizaciones
- ✅ Obtener estadísticas globales del sistema
- ✅ Ejecutar comandos en dispositivos de cualquier organización

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
> Esta API proporciona acceso administrativo completo al sistema.
>
> **Riesgos si se expone públicamente:**
> - Suplantación de identidad
> - Acceso no autorizado a datos de todas las organizaciones
> - Modificación de estados de organizaciones
> - Sin auditoría confiable
>
> **Medidas obligatorias:**
> 1. Proteger el endpoint `/api/v1/auth/internal` con firewall
> 2. Solo permitir acceso desde IPs de servicios autorizados
> 3. Usar VPN o red privada para comunicación
> 4. Implementar API Gateway con políticas restrictivas
> 5. Auditar regularmente los accesos

---

## Flujo de Autenticación para gac-web

### Paso 1: Obtener Token PASETO

```bash
curl -X POST https://api.example.com/api/v1/auth/internal \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@gac-web.internal",
    "service": "gac",
    "role": "NEXUS_ADMIN",
    "expires_in_hours": 8
  }'
```

#### Response

```json
{
  "token": "v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4uLi4...",
  "expires_at": "2024-01-15T18:30:00Z",
  "token_type": "Bearer"
}
```

### Paso 2: Usar el Token en las Peticiones

```bash
curl -X GET https://api.example.com/api/v1/internal/clients \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4uLi4..."
```

### Diagrama de Flujo

```
┌─────────────┐     1. POST /auth/internal      ┌─────────────┐
│   gac-web   │ ──────────────────────────────► │   API       │
│ (Admin App) │                                  │             │
│             │ ◄────────────────────────────── │             │
└─────────────┘     Token PASETO                └─────────────┘
      │
      │ Almacenar token
      ▼
┌─────────────┐     2. GET /internal/clients    ┌─────────────┐
│   gac-web   │ ──────────────────────────────► │   API       │
│             │     Authorization: Bearer ...    │             │
│             │ ◄────────────────────────────── │             │
└─────────────┘     Lista de organizaciones     └─────────────┘
```

---

## Endpoints

### 1. Listar Todas las Organizaciones

**GET** `/api/v1/internal/clients`

Lista todas las organizaciones del sistema con opciones de filtrado y paginación.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Query Parameters

| Parámetro | Tipo   | Requerido | Descripción |
|-----------|--------|-----------|-------------|
| `status`  | string | No | Filtrar por estado (PENDING, ACTIVE, SUSPENDED, DELETED) |
| `search`  | string | No | Buscar por nombre (parcial, case-insensitive) |
| `limit`   | int    | No | Máximo de resultados (default: 50, max: 200) |
| `offset`  | int    | No | Offset para paginación (default: 0) |

#### Ejemplo de Request

```bash
# Listar todas las organizaciones activas
curl -X GET "https://api.example.com/api/v1/internal/clients?status=ACTIVE&limit=20" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Buscar organizaciones por nombre
curl -X GET "https://api.example.com/api/v1/internal/clients?search=transportes" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
[
  {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Transportes XYZ",
    "status": "ACTIVE",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T15:45:00Z",
    "subscriptions_count": 2,
    "users_count": 5,
    "devices_count": 45
  },
  {
    "id": "567e4567-e89b-12d3-a456-426614174001",
    "name": "Logística ABC",
    "status": "ACTIVE",
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2024-01-10T08:00:00Z",
    "subscriptions_count": 1,
    "users_count": 3,
    "devices_count": 12
  }
]
```

> **Nota**: El campo `active_subscription_id` NO se incluye en la respuesta porque es deprecado. En su lugar, se incluye `subscriptions_count` para indicar suscripciones activas.

---

### 2. Obtener Estadísticas de Organizaciones

**GET** `/api/v1/internal/clients/stats`

Obtiene estadísticas generales del sistema.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Response 200 OK

```json
{
  "total": 150,
  "by_status": {
    "pending": 12,
    "active": 125,
    "suspended": 8,
    "deleted": 5
  },
  "subscriptions": {
    "total_active": 180,
    "by_plan": {
      "Plan Básico": 45,
      "Plan Pro": 80,
      "Plan Enterprise": 55
    }
  },
  "devices": {
    "total": 2500,
    "active": 2100
  }
}
```

---

### 3. Obtener Organización por ID

**GET** `/api/v1/internal/clients/{client_id}`

Obtiene información detallada de una organización específica, incluyendo sus suscripciones y capabilities.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro   | Tipo | Descripción |
|-------------|------|-------------|
| `client_id` | UUID | ID de la organización |

#### Response 200 OK

```json
{
  "organization": {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Transportes XYZ",
    "status": "ACTIVE",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T15:45:00Z"
  },
  "subscriptions": {
    "active": [
      {
        "id": "sub-uuid-1",
        "plan": {
          "id": "plan-uuid",
          "name": "Plan Enterprise"
        },
        "status": "ACTIVE",
        "started_at": "2024-01-01T00:00:00Z",
        "expires_at": "2025-01-01T00:00:00Z",
        "auto_renew": true
      }
    ],
    "history": [
      {
        "id": "sub-uuid-old",
        "plan": {
          "id": "plan-uuid-old",
          "name": "Plan Básico"
        },
        "status": "EXPIRED",
        "started_at": "2023-01-01T00:00:00Z",
        "expires_at": "2024-01-01T00:00:00Z"
      }
    ]
  },
  "effective_capabilities": {
    "max_devices": 100,
    "max_geofences": 50,
    "max_users": 25,
    "history_days": 365,
    "ai_features": true,
    "analytics_tools": true
  },
  "capability_overrides": [
    {
      "capability": "max_geofences",
      "value": 100,
      "reason": "Upgrade especial por volumen",
      "applied_at": "2024-06-01T00:00:00Z"
    }
  ],
  "stats": {
    "users_count": 5,
    "devices_count": 45,
    "units_count": 40
  }
}
```

#### Response 404 Not Found

```json
{
  "detail": "Cliente no encontrado"
}
```

---

### 4. Listar Usuarios de una Organización

**GET** `/api/v1/internal/clients/{client_id}/users`

Lista todos los usuarios de una organización con sus roles.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "admin@transportesxyz.com",
    "full_name": "Juan Pérez",
    "role": "owner",
    "is_master": true,
    "email_verified": true,
    "has_cognito": true,
    "last_login_at": "2024-01-20T10:00:00Z",
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": "234e4567-e89b-12d3-a456-426614174001",
    "email": "operador@transportesxyz.com",
    "full_name": "María García",
    "role": "admin",
    "is_master": true,
    "email_verified": true,
    "has_cognito": true,
    "last_login_at": "2024-01-19T15:30:00Z",
    "created_at": "2024-01-20T14:00:00Z"
  },
  {
    "id": "345e4567-e89b-12d3-a456-426614174002",
    "email": "contador@transportesxyz.com",
    "full_name": "Carlos López",
    "role": "billing",
    "is_master": false,
    "email_verified": true,
    "has_cognito": true,
    "created_at": "2024-02-01T09:00:00Z"
  }
]
```

---

### 5. Actualizar Estado de Organización

**PATCH** `/api/v1/internal/clients/{client_id}/status`

Actualiza el estado de una organización. Útil para suspender, activar o eliminar organizaciones.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Query Parameters

| Parámetro    | Tipo   | Requerido | Descripción |
|--------------|--------|-----------|-------------|
| `new_status` | string | Sí | Nuevo estado (PENDING, ACTIVE, SUSPENDED, DELETED) |

#### Estados y Transiciones

| Estado Actual | Estados Permitidos |
|---------------|-------------------|
| PENDING | ACTIVE, DELETED |
| ACTIVE | SUSPENDED, DELETED |
| SUSPENDED | ACTIVE, DELETED |
| DELETED | (ninguno - estado final) |

#### Ejemplo de Request

```bash
# Suspender una organización
curl -X PATCH "https://api.example.com/api/v1/internal/clients/456e4567-.../status?new_status=SUSPENDED" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Reactivar una organización
curl -X PATCH "https://api.example.com/api/v1/internal/clients/456e4567-.../status?new_status=ACTIVE" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
{
  "message": "Estado actualizado de ACTIVE a SUSPENDED",
  "organization": {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Transportes XYZ",
    "status": "SUSPENDED",
    "previous_status": "ACTIVE",
    "updated_at": "2024-01-20T16:00:00Z"
  },
  "affected": {
    "users_blocked": 5,
    "devices_suspended": 45
  }
}
```

---

### 6. Listar Suscripciones de una Organización

**GET** `/api/v1/internal/clients/{client_id}/subscriptions`

> **Estado**: Endpoint esperado para implementación

Lista todas las suscripciones de una organización (activas e históricas).

#### Response Esperado

```json
{
  "organization_id": "456e4567-e89b-12d3-a456-426614174000",
  "subscriptions": [
    {
      "id": "sub-uuid-1",
      "plan": {
        "id": "plan-uuid",
        "name": "Plan Enterprise",
        "capabilities": {
          "max_devices": 100,
          "max_geofences": 50
        }
      },
      "status": "ACTIVE",
      "started_at": "2024-01-01T00:00:00Z",
      "expires_at": "2025-01-01T00:00:00Z",
      "auto_renew": true,
      "payment_status": "CURRENT"
    }
  ],
  "total_active": 1,
  "total_expired": 2
}
```

---

### 7. Gestionar Capability Overrides

**POST** `/api/v1/internal/clients/{client_id}/capability-overrides`

> **Estado**: Endpoint esperado para implementación

Aplica un override de capability a una organización.

#### Request Body

```json
{
  "capability": "max_geofences",
  "value": 100,
  "reason": "Upgrade especial por contrato enterprise"
}
```

#### Response Esperado

```json
{
  "message": "Override aplicado exitosamente",
  "override": {
    "capability": "max_geofences",
    "previous_effective": 50,
    "new_effective": 100,
    "source": "organization_override",
    "applied_at": "2024-01-20T16:00:00Z"
  }
}
```

**DELETE** `/api/v1/internal/clients/{client_id}/capability-overrides/{capability}`

Elimina un override y vuelve al valor del plan.

---

## Casos de Uso del Orquestador

### 1. Suspender Organización por Falta de Pago

```bash
# 1. Verificar estado actual
GET /api/v1/internal/clients/{org_id}

# 2. Suspender organización
PATCH /api/v1/internal/clients/{org_id}/status?new_status=SUSPENDED

# 3. (Opcional) Notificar por email externo
```

### 2. Inspeccionar Capabilities de una Organización

```bash
# Obtener detalle completo
GET /api/v1/internal/clients/{org_id}

# Respuesta incluye effective_capabilities y capability_overrides
```

### 3. Aplicar Upgrade Especial a Organización

```bash
# 1. Verificar capabilities actuales
GET /api/v1/internal/clients/{org_id}

# 2. Aplicar override
POST /api/v1/internal/clients/{org_id}/capability-overrides
{
  "capability": "max_devices",
  "value": 200,
  "reason": "Contrato enterprise 2024"
}
```

### 4. Auditar Usuarios de una Organización

```bash
# Listar usuarios con roles
GET /api/v1/internal/clients/{org_id}/users

# Verificar quién tiene rol de billing
# Verificar último login de usuarios
```

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

### 404 Not Found

La organización solicitada no existe.

```json
{
  "detail": "Cliente no encontrado"
}
```

### 400 Bad Request

Transición de estado inválida.

```json
{
  "detail": "No se puede cambiar de DELETED a ACTIVE"
}
```

---

## Comparación: API Pública vs API Interna

| Aspecto | API Pública (`/clients`) | API Interna (`/internal/clients`) |
|---------|--------------------------|-----------------------------------|
| **Autenticación** | Cognito (usuarios externos) | PASETO (servicios internos) |
| **Acceso a datos** | Solo su propia organización | Todas las organizaciones |
| **Operaciones** | Lectura de su organización | CRUD completo + capabilities |
| **Caso de uso** | App de clientes finales | Panel administrativo (gac-web) |
| **Usuarios** | Clientes del sistema | Administradores internos |
| **Visibilidad** | Pública | Solo red interna |

---

## Notas de Seguridad

1. **Protección del endpoint de tokens**: El endpoint `POST /api/v1/auth/internal` debe estar protegido por firewall, VPN o API Gateway.

2. **Almacenamiento de tokens**: Los tokens PASETO deben almacenarse de forma segura en gac-web (variables de entorno, secretos de la aplicación).

3. **Tiempo de expiración**: Use tiempos de expiración cortos (8-24 horas) para minimizar el riesgo si un token se compromete.

4. **Auditoría**: Los tokens PASETO contienen el email del usuario. Use un email identificable para auditoría.

5. **Rotación de tokens**: Implemente lógica para renovar tokens antes de que expiren.

6. **Logs**: Registre todas las operaciones realizadas a través de la API interna para auditoría.

---

## Integración con gac-web

### Configuración Recomendada

```javascript
// config.js
const API_CONFIG = {
  baseUrl: process.env.API_BASE_URL,
  internalEndpoint: '/auth/internal',
  service: 'gac',
  role: 'NEXUS_ADMIN',
  tokenExpirationHours: 8
};
```

### Servicio de Cliente

```javascript
class InternalClientsService {
  constructor() {
    this.token = null;
    this.tokenExpiry = null;
  }

  async getToken() {
    if (this.token && this.tokenExpiry > new Date()) {
      return this.token;
    }

    const response = await fetch(`${API_CONFIG.baseUrl}/auth/internal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'admin@gac-web.internal',
        service: API_CONFIG.service,
        role: API_CONFIG.role,
        expires_in_hours: API_CONFIG.tokenExpirationHours
      })
    });

    const data = await response.json();
    this.token = data.token;
    this.tokenExpiry = new Date(data.expires_at);
    
    return this.token;
  }

  async listOrganizations(params = {}) {
    const token = await this.getToken();
    const queryString = new URLSearchParams(params).toString();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients?${queryString}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    return response.json();
  }

  async getOrganization(orgId) {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients/${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    return response.json();
  }

  async updateStatus(orgId, newStatus) {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients/${orgId}/status?new_status=${newStatus}`,
      {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    return response.json();
  }
}

export const internalClientsService = new InternalClientsService();
```

---

**Última actualización**: Diciembre 2025  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)
