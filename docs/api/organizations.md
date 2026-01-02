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

## Endpoints

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

## Casos de Uso

### Empresa con Múltiples Flotas

```
Account: "Transportes García S.A."
├── Organization: "Flota Norte" (default, creada en registro)
├── Organization: "Flota Sur" (creada después)
└── Organization: "Flota Centro" (creada después)
```

### Flujo de Creación

1. Usuario se registra → Se crea Account + Organization default
2. Usuario (owner) crea más organizaciones según necesite
3. Cada organización puede tener sus propios usuarios, dispositivos, suscripciones

---

## Notas

- Las organizaciones se crean en estado `ACTIVE`
- El usuario que crea la organización se añade automáticamente como `OWNER`
- Por defecto, `country` = `"MX"` y `timezone` = `"America/Mexico_City"`
- Solo se muestran organizaciones que no están en estado `DELETED`

