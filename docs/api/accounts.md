# API de Cuentas (Accounts)

## Descripción

Endpoints para gestionar la **raíz comercial** del cliente. Una cuenta (`Account`) representa la entidad de facturación y billing que puede contener una o más organizaciones.

> **Referencia**: [ADR-001: Modelo Account/Organization/User](../architecture/adr/001-account-organization-user-model.md)

---

## Modelo Conceptual

```
┌─────────────────────────────────────────────────────────────┐
│                      ACCOUNT                                 │
│  - Raíz comercial (billing, facturación)                    │
│  - name: puede repetirse                                    │
│  - billing_email, country, timezone, metadata               │
│  - Relación con: payments, organizations                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ 1:N
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORGANIZATION                              │
│  - Raíz operativa (permisos, uso diario)                    │
│  - Pertenece a Account                                      │
│  - users, devices, units, subscriptions                     │
└─────────────────────────────────────────────────────────────┘
```

### 🎯 Regla de Oro

> **Los nombres NO son identidad. Los UUID sí.**

---

## Campos del Modelo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único |
| `name` | string | Nombre de la cuenta (puede repetirse) |
| `status` | enum | Estado: ACTIVE, SUSPENDED, DELETED |
| `billing_email` | string | Email de facturación |
| `country` | string | Código ISO 3166-1 alpha-2 |
| `timezone` | string | Zona horaria IANA |
| `metadata` | JSONB | Metadatos adicionales (RFC, industry, etc.) |
| `created_at` | datetime | Fecha de creación |
| `updated_at` | datetime | Fecha de última actualización |

---

## Endpoints

### 1. Obtener Mi Account

**GET** `/api/v1/accounts/me`

Obtiene el Account del usuario autenticado a través de su organización.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_name": "Mi Empresa S.A.",
  "status": "ACTIVE",
  "billing_email": "facturacion@miempresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "metadata": {
    "rfc": "XAXX010101000",
    "industry": "transport"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 404 | `"Organización no encontrada"` / `"Account no encontrado"` |

---

### 2. Obtener Account por ID

**GET** `/api/v1/accounts/{account_id}`

Obtiene información de un Account específico. El usuario debe tener acceso (su organización pertenece al account).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `account_id` | UUID | ID del account |

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_name": "Mi Empresa S.A.",
  "status": "ACTIVE",
  "billing_email": "facturacion@miempresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "metadata": {},
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | `"No tienes acceso a este account"` |
| 404 | `"Account no encontrado"` |

---

### 3. Actualizar Account (Perfil Progresivo)

**PATCH** `/api/v1/accounts/{account_id}`

Actualiza el perfil del Account de forma progresiva. **Todos los campos son opcionales**.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Permisos

- ✅ Solo usuarios con rol `owner` pueden modificar

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `account_id` | UUID | ID del account |

#### Request Body

Todos los campos son opcionales:

```json
{
  "account_name": "Mi Empresa S.A. de C.V.",
  "billing_email": "nueva-facturacion@miempresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "metadata": {
    "rfc": "XAXX010101000",
    "industry": "transport",
    "employees": 50
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `account_name` | string | Nombre de la cuenta (puede repetirse) |
| `billing_email` | string | Email de facturación |
| `country` | string | Código ISO 3166-1 alpha-2 |
| `timezone` | string | Zona horaria IANA |
| `metadata` | object | Metadatos adicionales (se hace merge) |

#### Validaciones

| Validación | Resultado |
|------------|-----------|
| ❌ Unicidad de `account_name` | **NO SE VALIDA** |
| ❌ Campos fiscales obligatorios | **NO SE EXIGEN** |
| ✅ Formato de `billing_email` | SE VALIDA |
| ✅ Rol `owner` requerido | SE VALIDA |

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_name": "Mi Empresa S.A. de C.V.",
  "billing_email": "nueva-facturacion@miempresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "updated_at": "2024-01-25T10:00:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 403 | `"Se requiere uno de los siguientes roles: owner"` |
| 403 | `"No tienes acceso a este account"` |
| 404 | `"Account no encontrado"` |
| 422 | Error de validación |

---

## Comportamiento del PATCH

### Merge de Metadata

Cuando se actualiza `metadata`, se hace un **merge** con el metadata existente:

```json
// Metadata existente
{
  "rfc": "XAXX010101000",
  "industry": "transport"
}

// Request PATCH
{
  "metadata": {
    "employees": 50,
    "industry": "logistics"  // Sobrescribe
  }
}

// Resultado
{
  "rfc": "XAXX010101000",      // Preservado
  "industry": "logistics",     // Sobrescrito
  "employees": 50              // Agregado
}
```

### Propagación a Organization

Algunos campos se propagan automáticamente a la Organization default:

| Campo | Se propaga |
|-------|------------|
| `account_name` | ✅ (si el nombre coincidía) |
| `billing_email` | ✅ |
| `country` | ✅ |
| `timezone` | ✅ |
| `metadata` | ❌ |

---

## Estados de la Cuenta

| Estado | Descripción |
|--------|-------------|
| `ACTIVE` | Cuenta activa y operativa |
| `SUSPENDED` | Suspendida (falta de pago, violación TOS) |
| `DELETED` | Eliminación lógica |

---

## Casos de Uso

### Completar información fiscal

```json
PATCH /api/v1/accounts/123e4567-...

{
  "billing_email": "facturacion@empresa.com",
  "country": "MX",
  "metadata": {
    "rfc": "ABC123456789",
    "razon_social": "Mi Empresa S.A. de C.V.",
    "regimen_fiscal": "601"
  }
}
```

### Cambiar zona horaria

```json
PATCH /api/v1/accounts/123e4567-...

{
  "timezone": "America/Monterrey"
}
```

### Actualizar nombre de empresa

```json
PATCH /api/v1/accounts/123e4567-...

{
  "account_name": "Nuevo Nombre de Empresa S.A."
}
```

---

## Relaciones

### Con Organizations

```python
account.organizations  # List[Organization]

# En el futuro, una cuenta podrá tener múltiples organizaciones
Account "Grupo Corporativo"
├── Organization "Transportes Norte"
├── Organization "Transportes Sur"
└── Organization "Logística Central"
```

### Con Payments

```python
account.payments  # List[Payment]

# Los pagos pertenecen a la cuenta (billing centralizado)
payment.account_id  # UUID
```

---

## Flujo de Onboarding Progresivo

```
1. Registro Rápido (POST /clients)
   ├── account_name: "Mi Empresa"
   ├── email: "admin@empresa.com"
   └── password: "****"
   
   → Account creado con datos mínimos

2. Usuario verifica email y usa el sistema

3. Perfil Progresivo (PATCH /accounts/{id})
   ├── billing_email: "facturacion@empresa.com"
   ├── country: "MX"
   ├── timezone: "America/Mexico_City"
   └── metadata: { rfc: "...", ... }
   
   → Account actualizado cuando el usuario lo necesite
```

---

## Referencias

- [API de Onboarding (Clients)](./clients.md) - Registro inicial
- [ADR-001](../architecture/adr/001-account-organization-user-model.md) - Decisión arquitectónica
- [Modelo Organizacional](../guides/organizational-model.md)

---

**Última actualización**: Diciembre 2024
