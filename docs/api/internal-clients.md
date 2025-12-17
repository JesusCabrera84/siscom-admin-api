# API Interna de Clientes

## Descripción

Endpoints internos para gestión administrativa de clientes. Estos endpoints están diseñados para ser usados por aplicaciones administrativas internas como **gac-web**.

**Base URL**: `/api/v1/internal/clients`

---

## Autenticación

Estos endpoints requieren un **token PASETO** con:
- `service`: `"gac"`
- `role`: `"NEXUS_ADMIN"`

---

## ⚠️ Advertencia de Seguridad

> Estos endpoints proporcionan acceso administrativo completo a los datos de clientes.
> Asegúrese de:
> - Proteger el endpoint `/api/v1/auth/internal` que genera los tokens
> - Almacenar los tokens PASETO de forma segura
> - Usar tiempos de expiración apropiados

---

## Flujo de Autenticación para gac-web

### Paso 1: Obtener Token PASETO

Antes de usar estos endpoints, la aplicación gac-web debe obtener un token PASETO:

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
│             │                                  │             │
│             │ ◄────────────────────────────── │             │
└─────────────┘     Token PASETO                └─────────────┘
      │
      │ Almacenar token
      ▼
┌─────────────┐     2. GET /internal/clients    ┌─────────────┐
│   gac-web   │ ──────────────────────────────► │   API       │
│             │     Authorization: Bearer ...    │             │
│             │ ◄────────────────────────────── │             │
└─────────────┘     Lista de clientes           └─────────────┘
```

---

## Endpoints

### 1. Listar Todos los Clientes

**GET** `/api/v1/internal/clients`

Lista todos los clientes del sistema con opciones de filtrado y paginación.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Query Parameters

| Parámetro | Tipo   | Requerido | Descripción                                    |
|-----------|--------|-----------|------------------------------------------------|
| `status`  | string | No        | Filtrar por estado (PENDING, ACTIVE, SUSPENDED, DELETED) |
| `search`  | string | No        | Buscar por nombre (parcial, case-insensitive)  |
| `limit`   | int    | No        | Máximo de resultados (default: 50, max: 200)   |
| `offset`  | int    | No        | Offset para paginación (default: 0)            |

#### Ejemplo de Request

```bash
# Listar todos los clientes activos
curl -X GET "https://api.example.com/api/v1/internal/clients?status=ACTIVE&limit=20" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Buscar clientes por nombre
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
    "active_subscription_id": "789e4567-e89b-12d3-a456-426614174001",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T15:45:00Z"
  },
  {
    "id": "567e4567-e89b-12d3-a456-426614174001",
    "name": "Logística ABC",
    "status": "ACTIVE",
    "active_subscription_id": null,
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2024-01-10T08:00:00Z"
  }
]
```

---

### 2. Obtener Estadísticas de Clientes

**GET** `/api/v1/internal/clients/stats`

Obtiene estadísticas generales de los clientes del sistema.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Ejemplo de Request

```bash
curl -X GET "https://api.example.com/api/v1/internal/clients/stats" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
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

### 3. Obtener Cliente por ID

**GET** `/api/v1/internal/clients/{client_id}`

Obtiene la información detallada de un cliente específico.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro   | Tipo | Descripción        |
|-------------|------|--------------------|
| `client_id` | UUID | ID del cliente     |

#### Ejemplo de Request

```bash
curl -X GET "https://api.example.com/api/v1/internal/clients/456e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "name": "Transportes XYZ",
  "status": "ACTIVE",
  "active_subscription_id": "789e4567-e89b-12d3-a456-426614174001",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

#### Response 404 Not Found

```json
{
  "detail": "Cliente no encontrado"
}
```

---

### 4. Listar Usuarios de un Cliente

**GET** `/api/v1/internal/clients/{client_id}/users`

Lista todos los usuarios asociados a un cliente específico.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro   | Tipo | Descripción        |
|-------------|------|--------------------|
| `client_id` | UUID | ID del cliente     |

#### Ejemplo de Request

```bash
curl -X GET "https://api.example.com/api/v1/internal/clients/456e4567-e89b-12d3-a456-426614174000/users" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
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
    "is_master": false,
    "email_verified": true,
    "has_cognito": true,
    "created_at": "2024-01-20T14:00:00Z"
  }
]
```

#### Response 404 Not Found

```json
{
  "detail": "Cliente no encontrado"
}
```

---

### 5. Actualizar Estado de Cliente

**PATCH** `/api/v1/internal/clients/{client_id}/status`

Actualiza el estado de un cliente. Útil para suspender, activar o eliminar clientes.

#### Headers

```
Authorization: Bearer <token_paseto>
```

#### Path Parameters

| Parámetro   | Tipo | Descripción        |
|-------------|------|--------------------|
| `client_id` | UUID | ID del cliente     |

#### Query Parameters

| Parámetro    | Tipo   | Requerido | Descripción                                      |
|--------------|--------|-----------|--------------------------------------------------|
| `new_status` | string | Sí        | Nuevo estado (PENDING, ACTIVE, SUSPENDED, DELETED) |

#### Estados Disponibles

| Estado    | Descripción                                    |
|-----------|------------------------------------------------|
| PENDING   | Cliente pendiente de verificación de email     |
| ACTIVE    | Cliente activo con acceso completo al sistema  |
| SUSPENDED | Cliente suspendido sin acceso al sistema       |
| DELETED   | Cliente eliminado lógicamente                  |

#### Ejemplo de Request

```bash
# Suspender un cliente
curl -X PATCH "https://api.example.com/api/v1/internal/clients/456e4567-e89b-12d3-a456-426614174000/status?new_status=SUSPENDED" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."

# Reactivar un cliente
curl -X PATCH "https://api.example.com/api/v1/internal/clients/456e4567-e89b-12d3-a456-426614174000/status?new_status=ACTIVE" \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..."
```

#### Response 200 OK

```json
{
  "message": "Estado actualizado de ACTIVE a SUSPENDED",
  "client": {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Transportes XYZ",
    "status": "SUSPENDED"
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

## Errores Comunes

### 401 Unauthorized

Token PASETO inválido, expirado o con permisos insuficientes.

```json
{
  "detail": "Token inválido. Se requiere un token de Cognito válido o un token PASETO de servicio válido."
}
```

**Soluciones:**
1. Verificar que el token no haya expirado
2. Generar un nuevo token con `POST /api/v1/auth/internal`
3. Asegurarse de usar `service: "gac"` y `role: "NEXUS_ADMIN"`

### 404 Not Found

El cliente solicitado no existe.

```json
{
  "detail": "Cliente no encontrado"
}
```

---

## Integración con gac-web

### Configuración Recomendada

```javascript
// config.js
const API_CONFIG = {
  baseUrl: 'https://api.example.com/api/v1',
  internalEndpoint: '/auth/internal',
  service: 'gac',
  role: 'NEXUS_ADMIN',
  tokenExpirationHours: 8
};
```

### Ejemplo de Servicio en JavaScript

```javascript
// clientsService.js

class ClientsService {
  constructor() {
    this.token = null;
    this.tokenExpiry = null;
  }

  async getToken() {
    // Verificar si el token actual es válido
    if (this.token && this.tokenExpiry > new Date()) {
      return this.token;
    }

    // Obtener nuevo token
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

  async listClients(params = {}) {
    const token = await this.getToken();
    const queryString = new URLSearchParams(params).toString();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients?${queryString}`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    return response.json();
  }

  async getClient(clientId) {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients/${clientId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    return response.json();
  }

  async getClientUsers(clientId) {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients/${clientId}/users`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    return response.json();
  }

  async updateClientStatus(clientId, newStatus) {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients/${clientId}/status?new_status=${newStatus}`,
      {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    return response.json();
  }

  async getStats() {
    const token = await this.getToken();
    
    const response = await fetch(
      `${API_CONFIG.baseUrl}/internal/clients/stats`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    return response.json();
  }
}

export const clientsService = new ClientsService();
```

### Uso del Servicio

```javascript
// Ejemplo de uso
import { clientsService } from './clientsService';

// Listar clientes activos
const activeClients = await clientsService.listClients({ 
  status: 'ACTIVE', 
  limit: 20 
});

// Buscar clientes
const results = await clientsService.listClients({ 
  search: 'transportes' 
});

// Obtener estadísticas
const stats = await clientsService.getStats();
console.log(`Total clientes: ${stats.total}`);
console.log(`Activos: ${stats.by_status.active}`);

// Suspender un cliente
await clientsService.updateClientStatus(
  '456e4567-e89b-12d3-a456-426614174000', 
  'SUSPENDED'
);
```

---

## Comparación: API Pública vs API Interna

| Aspecto              | API Pública (`/clients`)       | API Interna (`/internal/clients`) |
|----------------------|--------------------------------|-----------------------------------|
| **Autenticación**    | Cognito (usuarios externos)    | PASETO (servicios internos)       |
| **Acceso a datos**   | Solo su propio cliente         | Todos los clientes                |
| **Operaciones**      | Lectura de su cliente          | CRUD completo                     |
| **Caso de uso**      | App de clientes finales        | Panel administrativo (gac-web)    |
| **Usuarios**         | Clientes del sistema           | Administradores internos          |

---

## Notas de Seguridad

1. **Protección del endpoint de tokens**: El endpoint `POST /api/v1/auth/internal` debe estar protegido por firewall, VPN o API Gateway.

2. **Almacenamiento de tokens**: Los tokens PASETO deben almacenarse de forma segura en gac-web (variables de entorno, secretos de la aplicación).

3. **Tiempo de expiración**: Use tiempos de expiración cortos (8-24 horas) para minimizar el riesgo si un token se compromete.

4. **Auditoría**: Los tokens PASETO contienen el email del usuario. Asegúrese de usar un email identificable para auditoría.

5. **Rotación de tokens**: Implemente lógica para renovar tokens antes de que expiren.

