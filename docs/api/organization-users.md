# API de Usuarios de Organización

## Descripción

Endpoints para gestionar usuarios y roles dentro de una organización. Permite agregar usuarios, modificar roles, listar miembros y eliminar usuarios de una organización específica.

### Sistema de Roles Jerárquico

Los roles en una organización siguen una jerarquía de permisos:

```
owner > admin > billing > member
```

| Rol | Permisos |
|-----|----------|
| `owner` | Control total de la organización, puede modificar cualquier aspecto |
| `admin` | Gestión de usuarios y configuración (excepto owners) |
| `billing` | Acceso a facturación, pagos y suscripciones |
| `member` | Acceso operativo estándar |

---

## Reglas de Negocio

1. ✅ **Solo owner puede asignar otro owner**
2. ❌ **Admin NO puede modificar ni eliminar owners**
3. ⚠️ **No se puede eliminar ni degradar al ÚLTIMO owner**
4. 🔒 **Un usuario solo puede aparecer una vez por organización**
5. 📊 **Los usuarios deben existir en el sistema antes de agregarlos**

---

## Endpoints

### 1. Listar Usuarios de una Organización

**GET** `/api/v1/organizations/{organization_id}/users`

Lista todos los usuarios que pertenecen a una organización con sus roles.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |

#### Response 200 OK

```json
{
  "users": [
    {
      "id": "abc12345-e89b-12d3-a456-426614174000",
      "organization_id": "789e4567-e89b-12d3-a456-426614174000",
      "user_id": "456e4567-e89b-12d3-a456-426614174000",
      "email": "owner@empresa.com",
      "full_name": "Juan Pérez",
      "role": "owner",
      "created_at": "2024-01-15T08:00:00Z",
      "email_verified": true
    },
    {
      "id": "def67890-e89b-12d3-a456-426614174000",
      "organization_id": "789e4567-e89b-12d3-a456-426614174000",
      "user_id": "567f5678-e89b-12d3-a456-426614174001",
      "email": "admin@empresa.com",
      "full_name": "María García",
      "role": "admin",
      "created_at": "2024-01-16T10:00:00Z",
      "email_verified": true
    }
  ],
  "total": 2
}
```

#### Permisos

- Requiere rol: `member` o superior
- El usuario debe pertenecer al mismo Account que la organización

---

### 2. Agregar Usuario a Organización

**POST** `/api/v1/organizations/{organization_id}/users`

Agrega un usuario existente a la organización con un rol específico.

#### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |

#### Request Body

```json
{
  "user_id": "567f5678-e89b-12d3-a456-426614174001",
  "role": "admin"
}
```

**Campos:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `user_id` | UUID | Sí | ID del usuario a agregar (debe existir) |
| `role` | string | Sí | Rol a asignar: `owner`, `admin`, `billing`, `member` |

#### Response 201 Created

```json
{
  "id": "def67890-e89b-12d3-a456-426614174000",
  "organization_id": "789e4567-e89b-12d3-a456-426614174000",
  "user_id": "567f5678-e89b-12d3-a456-426614174001",
  "email": "admin@empresa.com",
  "full_name": "María García",
  "role": "admin",
  "created_at": "2024-01-16T10:00:00Z",
  "email_verified": true
}
```

#### Permisos

- Requiere rol: `admin` o superior
- Para asignar rol `owner`, el actor debe ser `owner`

#### Errores

**403 Forbidden** - Sin permisos para asignar el rol
```json
{
  "detail": "No tienes permisos para asignar el rol 'owner'"
}
```

**404 Not Found** - Usuario no existe
```json
{
  "detail": "Usuario no encontrado"
}
```

**409 Conflict** - Usuario ya es miembro
```json
{
  "detail": "El usuario ya es miembro de esta organización"
}
```

---

### 3. Actualizar Rol de Usuario

**PATCH** `/api/v1/organizations/{organization_id}/users/{user_id}`

Actualiza el rol de un usuario existente en la organización.

#### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |
| `user_id` | UUID | ID del usuario |

#### Request Body

```json
{
  "role": "billing"
}
```

**Campos:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `role` | string | Sí | Nuevo rol: `owner`, `admin`, `billing`, `member` |

#### Response 200 OK

```json
{
  "id": "def67890-e89b-12d3-a456-426614174000",
  "organization_id": "789e4567-e89b-12d3-a456-426614174000",
  "user_id": "567f5678-e89b-12d3-a456-426614174001",
  "email": "admin@empresa.com",
  "full_name": "María García",
  "role": "billing",
  "created_at": "2024-01-16T10:00:00Z",
  "email_verified": true
}
```

#### Permisos

- Requiere rol: `admin` o superior
- Para asignar rol `owner`, el actor debe ser `owner`
- Admin NO puede modificar owners

#### Errores

**400 Bad Request** - No se puede degradar al último owner
```json
{
  "detail": "No se puede degradar al último owner de la organización"
}
```

**403 Forbidden** - Sin permisos
```json
{
  "detail": "No tienes permisos para modificar a este usuario"
}
```

**404 Not Found** - Usuario no encontrado en organización
```json
{
  "detail": "Usuario no encontrado en la organización"
}
```

---

### 4. Eliminar Usuario de Organización

**DELETE** `/api/v1/organizations/{organization_id}/users/{user_id}`

Elimina un usuario de la organización. El usuario seguirá existiendo en el sistema, pero ya no será miembro de esta organización.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |
| `user_id` | UUID | ID del usuario a eliminar |

#### Response 204 No Content

Sin cuerpo de respuesta.

#### Permisos

- Requiere rol: `admin` o superior
- Admin NO puede eliminar owners
- No se puede eliminar al último owner

#### Errores

**400 Bad Request** - No se puede eliminar al último owner
```json
{
  "detail": "No se puede eliminar al último owner de la organización"
}
```

**403 Forbidden** - Sin permisos
```json
{
  "detail": "No tienes permisos para eliminar a este usuario"
}
```

**404 Not Found** - Usuario no encontrado
```json
{
  "detail": "Usuario no encontrado en la organización"
}
```

---

## Casos de Uso

### 1. Agregar Administrador

Agregar un usuario existente como administrador:

```bash
curl -X POST "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/users" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "567f5678-e89b-12d3-a456-426614174001",
    "role": "admin"
  }'
```

### 2. Degradar Usuario a Member

Cambiar el rol de un administrador a miembro:

```bash
curl -X PATCH "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/users/567f5678-e89b-12d3-a456-426614174001" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "member"
  }'
```

### 3. Transferir Ownership

Proceso para transferir el control de la organización:

**Paso 1**: Promover nuevo usuario a owner (requiere ser owner actual)
```bash
curl -X PATCH "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/users/567f5678-e89b-12d3-a456-426614174001" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "owner"
  }'
```

**Paso 2**: Degradar el owner anterior (ahora hay 2 owners)
```bash
curl -X PATCH "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/users/456e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
```

### 4. Eliminar Usuario

Remover un usuario de la organización:

```bash
curl -X DELETE "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/users/567f5678-e89b-12d3-a456-426614174001" \
  -H "Authorization: Bearer <access_token>"
```

### 5. Listar Miembros del Equipo

Consultar todos los usuarios de la organización:

```bash
curl -X GET "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/users" \
  -H "Authorization: Bearer <access_token>"
```

---

## Matriz de Permisos

### Qué Puede Hacer Cada Rol

| Acción | Owner | Admin | Billing | Member |
|--------|-------|-------|---------|--------|
| Ver lista de usuarios | ✅ | ✅ | ✅ | ✅ |
| Agregar member | ✅ | ✅ | ❌ | ❌ |
| Agregar billing | ✅ | ✅ | ❌ | ❌ |
| Agregar admin | ✅ | ✅ | ❌ | ❌ |
| Agregar owner | ✅ | ❌ | ❌ | ❌ |
| Modificar member | ✅ | ✅ | ❌ | ❌ |
| Modificar billing | ✅ | ✅ | ❌ | ❌ |
| Modificar admin | ✅ | ✅ | ❌ | ❌ |
| Modificar owner | ✅ | ❌ | ❌ | ❌ |
| Eliminar member | ✅ | ✅ | ❌ | ❌ |
| Eliminar billing | ✅ | ✅ | ❌ | ❌ |
| Eliminar admin | ✅ | ✅ | ❌ | ❌ |
| Eliminar owner | ✅ | ❌ | ❌ | ❌ |

---

## Notas Técnicas

### Auditoría

Todas las operaciones se registran en el sistema de auditoría:
- `org_user_added`: Usuario agregado a organización
- `org_user_role_changed`: Rol modificado
- `org_user_removed`: Usuario eliminado

Cada evento incluye:
- Actor (quién realizó la acción)
- Target (usuario afectado)
- Timestamp
- IP y User-Agent
- Detalles específicos (rol anterior, nuevo rol, etc.)

### Multi-Organización

Un usuario puede pertenecer a **múltiples organizaciones** dentro del mismo Account con **roles diferentes** en cada una. Las organizaciones están aisladas entre sí.

### Eliminación vs Desactivación

- `DELETE /organizations/{id}/users/{user_id}`: Elimina la **membresía** en la organización
- El usuario **NO se elimina del sistema**
- El usuario puede volver a ser agregado posteriormente

### Protección de Último Owner

El sistema protege activamente contra quedarse sin owners:
- No se puede degradar al último owner
- No se puede eliminar al último owner
- Se puede tener múltiples owners simultáneamente

### Acceso Multi-Account

Los usuarios solo pueden gestionar organizaciones dentro del **mismo Account**. Las organizaciones de diferentes Accounts están completamente aisladas.

---

## Referencias

- [API de Usuarios](./users.md) - Gestión de usuarios
- [API de Organizaciones](./organizations.md) - Gestión de organizaciones
- [API de Accounts](./accounts.md) - Gestión de cuentas
- [Modelo Organizacional](../guides/organizational-model.md) - Arquitectura de permisos
