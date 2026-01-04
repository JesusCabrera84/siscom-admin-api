# API de Organizaciones

## Descripción

Endpoints para gestión de **Organizations** (raíz operativa). Un Account puede tener múltiples Organizations.

> **Referencia**: [ADR-001: Modelo Account/Organization/User](../architecture/adr/001-account-organization-user-model.md)

---

## Modelo Conceptual

```
Account (1) ──< Organization (N)
```

- **Account** = Raíz comercial (billing, facturación)
- **Organization** = Raíz operativa (permisos, uso diario, dispositivos, usuarios)

Una empresa puede tener múltiples organizaciones (ej: flotas, sucursales, divisiones).

---

## Índice de Endpoints

### Organizaciones
- `POST /api/v1/organizations` - Crear organización
- `GET /api/v1/organizations` - Listar organizaciones
- `GET /api/v1/organizations/{id}` - Obtener organización
- `PATCH /api/v1/organizations/{id}` - Actualizar organización

### Usuarios de Organización
- `GET /api/v1/organizations/{id}/users` - Listar usuarios
- `POST /api/v1/organizations/{id}/users` - Agregar usuario
- `PATCH /api/v1/organizations/{id}/users/{user_id}` - Cambiar rol
- `DELETE /api/v1/organizations/{id}/users/{user_id}` - Eliminar usuario

### Capabilities de Organización
- `GET /api/v1/organizations/{id}/capabilities` - Listar capabilities
- `POST /api/v1/organizations/{id}/capabilities` - Crear/actualizar override
- `DELETE /api/v1/organizations/{id}/capabilities/{code}` - Eliminar override

---

## Endpoints de Organizaciones

### 1. Crear Organización

**POST** `/api/v1/organizations`

Crea una nueva organización dentro del Account del usuario.

#### Permisos

Solo usuarios con rol `owner` pueden crear organizaciones.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "name": "Flota Norte",
  "billing_email": "flotanorte@empresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City"
}
```

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `name` | string | ✅ | - | Nombre de la organización |
| `billing_email` | string | ❌ | null | Email de facturación |
| `country` | string | ❌ | `"MX"` | Código ISO 3166-1 alpha-2 |
| `timezone` | string | ❌ | `"America/Mexico_City"` | Zona horaria IANA |

#### Response 201 Created

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_id": "223e4567-e89b-12d3-a456-426614174000",
  "name": "Flota Norte",
  "status": "ACTIVE",
  "billing_email": "flotanorte@empresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | No tienes rol de owner |
| 404 | Organización actual no encontrada |

---

### 2. Listar Organizaciones

**GET** `/api/v1/organizations`

Lista todas las organizaciones del Account del usuario.

#### Permisos

Cualquier usuario autenticado con rol `member` o superior.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "account_id": "223e4567-e89b-12d3-a456-426614174000",
    "name": "Flota Norte",
    "status": "ACTIVE",
    "billing_email": "flotanorte@empresa.com",
    "country": "MX",
    "timezone": "America/Mexico_City",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": "323e4567-e89b-12d3-a456-426614174000",
    "account_id": "223e4567-e89b-12d3-a456-426614174000",
    "name": "Flota Sur",
    "status": "ACTIVE",
    "billing_email": null,
    "country": "MX",
    "timezone": "America/Mexico_City",
    "created_at": "2024-02-01T08:00:00Z",
    "updated_at": "2024-02-01T08:00:00Z"
  }
]
```

---

### 3. Obtener Organización por ID

**GET** `/api/v1/organizations/{organization_id}`

Obtiene información de una organización específica.

#### Permisos

Cualquier usuario autenticado. Solo permite acceder a organizaciones del mismo Account.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_id": "223e4567-e89b-12d3-a456-426614174000",
  "name": "Flota Norte",
  "status": "ACTIVE",
  "billing_email": "flotanorte@empresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | No tienes acceso a esta organización |
| 404 | Organización no encontrada |

---

### 4. Actualizar Organización

**PATCH** `/api/v1/organizations/{organization_id}`

Actualiza una organización existente.

#### Permisos

Solo usuarios con rol `owner` pueden actualizar organizaciones.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

Todos los campos son opcionales:

```json
{
  "name": "Flota Norte - Actualizada",
  "billing_email": "nuevo-email@empresa.com",
  "country": "MX",
  "timezone": "America/Monterrey"
}
```

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_id": "223e4567-e89b-12d3-a456-426614174000",
  "name": "Flota Norte - Actualizada",
  "status": "ACTIVE",
  "billing_email": "nuevo-email@empresa.com",
  "country": "MX",
  "timezone": "America/Monterrey",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | No tienes rol de owner / No tienes acceso |
| 404 | Organización no encontrada |

---

## Endpoints de Usuarios de Organización

### Sistema de Roles

```
owner > admin > billing > member
```

| Rol | Descripción | Permisos |
|-----|-------------|----------|
| `owner` | Control total de la organización | Todo |
| `admin` | Gestión de usuarios y configuración | Gestionar usuarios (excepto owner), configuración |
| `billing` | Gestión financiera | Pagos, suscripciones, facturación |
| `member` | Acceso operativo | Solo lectura y operaciones básicas |

### Reglas de Negocio

1. **Solo owner puede asignar otro owner**
2. **Admin NO puede modificar a owners**
3. **No se puede eliminar ni degradar al ÚLTIMO owner**
4. **Un usuario solo puede aparecer una vez por organización**

---

### 5. Listar Usuarios de Organización

**GET** `/api/v1/organizations/{organization_id}/users`

Lista todos los usuarios de una organización con sus roles.

#### Permisos

Cualquier miembro de la organización (`member` o superior).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "users": [
    {
      "id": "membership-uuid-001",
      "organization_id": "123e4567-e89b-12d3-a456-426614174000",
      "user_id": "user-uuid-001",
      "email": "owner@empresa.com",
      "full_name": "Carlos López",
      "role": "owner",
      "created_at": "2024-01-01T00:00:00Z",
      "email_verified": true
    },
    {
      "id": "membership-uuid-002",
      "organization_id": "123e4567-e89b-12d3-a456-426614174000",
      "user_id": "user-uuid-002",
      "email": "admin@empresa.com",
      "full_name": "María Pérez",
      "role": "admin",
      "created_at": "2024-01-15T10:30:00Z",
      "email_verified": true
    }
  ],
  "total": 2
}
```

---

### 6. Agregar Usuario a Organización

**POST** `/api/v1/organizations/{organization_id}/users`

Agrega un usuario existente a la organización con un rol específico.

#### Permisos

- Rol `admin` o superior
- Solo `owner` puede asignar rol `owner`

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "user_id": "user-uuid-003",
  "role": "member"
}
```

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `user_id` | UUID | ✅ | - | ID del usuario a agregar |
| `role` | string | ❌ | `"member"` | Rol a asignar: `owner`, `admin`, `billing`, `member` |

#### Response 201 Created

```json
{
  "id": "membership-uuid-003",
  "organization_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-uuid-003",
  "email": "nuevo@empresa.com",
  "full_name": "Pedro Martínez",
  "role": "member",
  "created_at": "2024-01-20T15:00:00Z",
  "email_verified": false
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | No tienes permisos para gestionar usuarios |
| 403 | No tienes permisos para asignar el rol 'owner' |
| 404 | Usuario no encontrado |
| 404 | Organización no encontrada |
| 409 | El usuario ya es miembro de esta organización |

---

### 7. Cambiar Rol de Usuario

**PATCH** `/api/v1/organizations/{organization_id}/users/{user_id}`

Actualiza el rol de un usuario en la organización.

#### Permisos

- Rol `admin` o superior
- Admin NO puede modificar a owners
- Solo `owner` puede asignar rol `owner`

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "role": "admin"
}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `role` | string | ✅ | Nuevo rol: `owner`, `admin`, `billing`, `member` |

#### Response 200 OK

```json
{
  "id": "membership-uuid-002",
  "organization_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-uuid-002",
  "email": "usuario@empresa.com",
  "full_name": "María Pérez",
  "role": "admin",
  "created_at": "2024-01-15T10:30:00Z",
  "email_verified": true
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | No tienes permisos para gestionar usuarios |
| 403 | No tienes permisos para modificar a este usuario |
| 403 | No tienes permisos para asignar el rol 'owner' |
| 400 | No se puede degradar al último owner de la organización |
| 404 | Usuario no encontrado en la organización |

---

### 8. Eliminar Usuario de Organización

**DELETE** `/api/v1/organizations/{organization_id}/users/{user_id}`

Elimina un usuario de la organización.

#### Permisos

- Rol `admin` o superior
- Admin NO puede eliminar a owners
- No se puede eliminar al último owner

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 204 No Content

Sin cuerpo de respuesta.

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | No tienes permisos para gestionar usuarios |
| 403 | No tienes permisos para eliminar a este usuario |
| 400 | No se puede eliminar al último owner de la organización |
| 404 | Usuario no encontrado en la organización |

---

## Endpoints de Capabilities de Organización

### Sistema de Capabilities

Las capabilities determinan límites y features de una organización. Se resuelven con la regla:

```
organization_override ?? plan_capability ?? default
```

> **Nota**: Estos endpoints gestionan los **overrides** específicos de la organización. Para consultas generales, ver [API de Capabilities](./capabilities.md).

---

### 9. Listar Capabilities de Organización

**GET** `/api/v1/organizations/{organization_id}/capabilities`

Lista todas las capabilities efectivas de una organización, indicando la fuente de cada valor.

#### Permisos

Cualquier miembro de la organización (`member` o superior).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "capabilities": [
    {
      "code": "max_devices",
      "value": 100,
      "value_type": "int",
      "source": "organization",
      "plan_id": null,
      "expires_at": "2025-12-31T23:59:59Z",
      "is_override": true
    },
    {
      "code": "max_users",
      "value": 10,
      "value_type": "int",
      "source": "plan",
      "plan_id": "plan-uuid-001",
      "expires_at": null,
      "is_override": false
    },
    {
      "code": "ai_features",
      "value": false,
      "value_type": "bool",
      "source": "default",
      "plan_id": null,
      "expires_at": null,
      "is_override": false
    }
  ],
  "total": 3,
  "overrides_count": 1
}
```

#### Campos de Respuesta

| Campo | Descripción |
|-------|-------------|
| `code` | Código único de la capability |
| `value` | Valor efectivo (int, bool, o string) |
| `value_type` | Tipo de valor: `int`, `bool`, `text` |
| `source` | Fuente: `organization`, `plan`, `default` |
| `plan_id` | ID del plan (si source = plan) |
| `expires_at` | Fecha de expiración del override |
| `is_override` | Si es un override de organización |

---

### 10. Crear/Actualizar Override de Capability

**POST** `/api/v1/organizations/{organization_id}/capabilities`

Crea o actualiza un override de capability para la organización.

#### Permisos

Solo usuarios con rol `owner`.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "capability_code": "max_devices",
  "value_int": 100,
  "reason": "Promoción especial Q4 2024",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `capability_code` | string | ✅ | Código de la capability |
| `value_int` | int | ❌* | Valor para capabilities de tipo int |
| `value_bool` | bool | ❌* | Valor para capabilities de tipo bool |
| `value_text` | string | ❌* | Valor para capabilities de tipo text |
| `reason` | string | ❌ | Razón del override |
| `expires_at` | datetime | ❌ | Fecha de expiración |

*Se debe proporcionar exactamente uno de: `value_int`, `value_bool`, `value_text`

#### Response 201 Created

```json
{
  "organization_id": "123e4567-e89b-12d3-a456-426614174000",
  "capability_id": "cap-uuid-001",
  "capability_code": "max_devices",
  "value": 100,
  "value_type": "int",
  "source": "organization",
  "reason": "Promoción especial Q4 2024",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 400 | Debe proporcionar un valor (value_int, value_bool o value_text) |
| 401 | Token no proporcionado o inválido |
| 403 | No tienes rol de owner |
| 404 | Capability 'xxx' no encontrada |
| 404 | Organización no encontrada |

---

### 11. Eliminar Override de Capability

**DELETE** `/api/v1/organizations/{organization_id}/capabilities/{capability_code}`

Elimina un override de capability. La organización volverá a usar el valor del plan o default.

#### Permisos

Solo usuarios con rol `owner`.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 204 No Content

Sin cuerpo de respuesta.

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | No tienes rol de owner |
| 404 | Override de capability 'xxx' no encontrado |
| 404 | Organización no encontrada |

---

## Auditoría

Todas las acciones de usuarios y capabilities se registran en la tabla `account_events`:

| Evento | Descripción |
|--------|-------------|
| `org_user_added` | Usuario agregado a organización |
| `org_user_removed` | Usuario eliminado de organización |
| `org_user_role_changed` | Rol de usuario cambiado |
| `org_capability_created` | Override de capability creado |
| `org_capability_updated` | Override de capability actualizado |
| `org_capability_deleted` | Override de capability eliminado |

Los eventos incluyen:
- `account_id` y `organization_id`
- `actor_user_id` (quién realizó la acción)
- `target_id` (usuario o capability afectado)
- `metadata` (detalles adicionales: roles, valores, etc.)
- `ip_address` y `user_agent`

---

## Casos de Uso

### Empresa con Múltiples Flotas

```
Account: "Transportes García S.A."
├── Organization: "Flota Norte" (default, creada en registro)
│   ├── owner: Carlos García
│   ├── admin: María López
│   └── member: Juan Pérez (operador)
├── Organization: "Flota Sur" (creada después)
│   ├── owner: Carlos García
│   └── admin: Ana Martínez
└── Organization: "Flota Centro" (creada después)
    └── owner: Carlos García
```

### Flujo de Creación

1. Usuario se registra → Se crea Account + Organization default
2. Usuario (owner) crea más organizaciones según necesite
3. Owner agrega usuarios a cada organización con roles apropiados
4. Cada organización puede tener sus propios usuarios, dispositivos, suscripciones

### Promoción de Capabilities

```bash
# Dar 100 dispositivos extra por 3 meses
POST /api/v1/organizations/{org_id}/capabilities
{
  "capability_code": "max_devices",
  "value_int": 100,
  "reason": "Promoción Q1 2025",
  "expires_at": "2025-03-31T23:59:59Z"
}
```

---

## Ejemplos con cURL

### Listar Usuarios

```bash
curl -X GET "http://localhost:8000/api/v1/organizations/{org_id}/users" \
  -H "Authorization: Bearer <token>"
```

### Agregar Usuario

```bash
curl -X POST "http://localhost:8000/api/v1/organizations/{org_id}/users" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "role": "admin"
  }'
```

### Cambiar Rol

```bash
curl -X PATCH "http://localhost:8000/api/v1/organizations/{org_id}/users/{user_id}" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "billing"
  }'
```

### Listar Capabilities

```bash
curl -X GET "http://localhost:8000/api/v1/organizations/{org_id}/capabilities" \
  -H "Authorization: Bearer <token>"
```

### Crear Override

```bash
curl -X POST "http://localhost:8000/api/v1/organizations/{org_id}/capabilities" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_code": "max_devices",
    "value_int": 50,
    "reason": "Acuerdo especial"
  }'
```

### Eliminar Override

```bash
curl -X DELETE "http://localhost:8000/api/v1/organizations/{org_id}/capabilities/max_devices" \
  -H "Authorization: Bearer <token>"
```

---

## Notas

- Las organizaciones se crean en estado `ACTIVE`
- El usuario que crea la organización se añade automáticamente como `OWNER`
- Por defecto, `country` = `"MX"` y `timezone` = `"America/Mexico_City"`
- Solo se muestran organizaciones que no están en estado `DELETED`
- Los overrides de capability sin `expires_at` son permanentes
- Al eliminar un override, el valor vuelve a resolverse desde el plan o default

---

**Última actualización**: Enero 2026  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)
