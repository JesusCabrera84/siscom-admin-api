# API Interna - Orquestador Administrativo

## Descripción

La API interna proporciona endpoints administrativos para gestión global del sistema. Funciona como un **orquestador administrativo** que permite operaciones cross-organization que no están disponibles para usuarios regulares.

> **Rol**: Panel de administración interno para operaciones que trascienden el contexto de una sola organización.

**Base URL**: `/api/v1/internal/organizations`

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
curl -X GET https://api.example.com/api/v1/internal/organizations \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4uLi4..."
```

### Diagrama de Flujo

```
┌─────────────┐     1. POST /auth/internal          ┌─────────────┐
│   gac-web   │ ───────────────────────────────────► │   API       │
│ (Admin App) │                                      │             │
│             │ ◄─────────────────────────────────── │             │
└─────────────┘     Token PASETO                     └─────────────┘
      │
      │ Almacenar token
      ▼
┌─────────────┐     2. GET /internal/organizations  ┌─────────────┐
│   gac-web   │ ───────────────────────────────────► │   API       │
│             │     Authorization: Bearer ...        │             │
│             │ ◄─────────────────────────────────── │             │
└─────────────┘     Lista de organizaciones          └─────────────┘
```

---

## Endpoints

### 1. Listar Todas las Organizaciones

**GET** `/api/v1/internal/organizations`

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
curl -X GET "https://api.example.com/api/v1/internal/organizations?status=ACTIVE&limit=20" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Buscar organizaciones por nombre
curl -X GET "https://api.example.com/api/v1/internal/organizations?search=transportes" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
[
  {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "account_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Transportes XYZ",
    "status": "ACTIVE",
    "billing_email": "facturacion@transportesxyz.com",
    "country": "MX",
    "timezone": "America/Mexico_City",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T15:45:00Z"
  },
  {
    "id": "567e4567-e89b-12d3-a456-426614174001",
    "account_id": "234e4567-e89b-12d3-a456-426614174001",
    "name": "Logística ABC",
    "status": "ACTIVE",
    "billing_email": "admin@logisticaabc.com",
    "country": "MX",
    "timezone": "America/Mexico_City",
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2024-01-10T08:00:00Z"
  }
]
```

---

### 2. Obtener Estadísticas de Organizaciones

**GET** `/api/v1/internal/organizations/stats`

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
  }
}
```

---

### 3. Obtener Organización por ID

**GET** `/api/v1/internal/organizations/{organization_id}`

Obtiene información detallada de una organización específica.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |

#### Response 200 OK

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "account_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Transportes XYZ",
  "status": "ACTIVE",
  "billing_email": "facturacion@transportesxyz.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

#### Response 404 Not Found

```json
{
  "detail": "Organización no encontrada"
}
```

---

### 4. Listar Usuarios de una Organización

**GET** `/api/v1/internal/organizations/{organization_id}/users`

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
    "is_master": true,
    "email_verified": true,
    "has_cognito": true,
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": "234e4567-e89b-12d3-a456-426614174001",
    "email": "operador@transportesxyz.com",
    "full_name": "María García",
    "is_master": true,
    "email_verified": true,
    "has_cognito": true,
    "created_at": "2024-01-20T14:00:00Z"
  }
]
```

---

### 5. Actualizar Estado de Organización

**PATCH** `/api/v1/internal/organizations/{organization_id}/status`

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
curl -X PATCH "https://api.example.com/api/v1/internal/organizations/456e4567-.../status?new_status=SUSPENDED" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Reactivar una organización
curl -X PATCH "https://api.example.com/api/v1/internal/organizations/456e4567-.../status?new_status=ACTIVE" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
{
  "message": "Estado actualizado de ACTIVE a SUSPENDED",
  "organization": {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Transportes XYZ",
    "status": "SUSPENDED"
  }
}
```

---

## Casos de Uso del Orquestador

### 1. Suspender Organización por Falta de Pago

```bash
# 1. Verificar estado actual
GET /api/v1/internal/organizations/{org_id}

# 2. Suspender organización
PATCH /api/v1/internal/organizations/{org_id}/status?new_status=SUSPENDED
```

### 2. Auditar Usuarios de una Organización

```bash
# Listar usuarios
GET /api/v1/internal/organizations/{org_id}/users

# Verificar quién es master
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
  "detail": "Organización no encontrada"
}
```

---

## Comparación: API Pública vs API Interna

| Aspecto | API Pública (`/accounts`) | API Interna (`/internal/organizations`) |
|---------|---------------------------|----------------------------------------|
| **Autenticación** | Cognito (usuarios externos) | PASETO (servicios internos) |
| **Acceso a datos** | Solo su propia organización | Todas las organizaciones |
| **Operaciones** | CRUD de su account/org | CRUD completo + capabilities |
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
class InternalOrganizationsService {
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
      `${API_CONFIG.baseUrl}/internal/organizations?${queryString}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    return response.json();
  }

  async getOrganization(orgId) {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/organizations/${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    return response.json();
  }

  async updateStatus(orgId, newStatus) {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/organizations/${orgId}/status?new_status=${newStatus}`,
      {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    return response.json();
  }
}

export const internalOrganizationsService = new InternalOrganizationsService();
```

---

---

## Relación con Otros Endpoints

| Endpoint | Propósito |
|----------|-----------|
| `GET /internal/accounts/stats` | Estadísticas globales (accounts, devices, users) |
| `GET /internal/organizations` | Lista todas las organizaciones (este endpoint) |
| `GET /internal/organizations/stats` | Estadísticas de organizaciones por estado |

---

**Última actualización**: Enero 2026  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md) | [API Interna - Accounts](internal-accounts.md)

