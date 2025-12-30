# API de Onboarding

## Descripción

Endpoint para **onboarding rápido** de nuevos clientes. Crea la estructura completa Account + Organization + User con validación mínima.

> **Referencia**: [ADR-001: Modelo Account/Organization/User](../architecture/adr/001-account-organization-user-model.md)

---

## Modelo Conceptual

```
┌─────────────────────────────────────────────────────────────┐
│                      ACCOUNT                                 │
│  - Raíz comercial (billing, facturación)                    │
│  - name: puede repetirse                                    │
│  - billing_email, country, timezone, metadata               │
└─────────────────────────┬───────────────────────────────────┘
                          │ 1:N
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORGANIZATION                              │
│  - Raíz operativa (permisos, uso diario)                    │
│  - name: puede repetirse globalmente                        │
│  - Pertenece a Account                                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ 1:N
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        USER                                  │
│  - email: DEBE ser único globalmente                        │
│  - Roles via OrganizationUser                               │
└─────────────────────────────────────────────────────────────┘
```

### 🎯 Regla de Oro

> **Los nombres NO son identidad. Los UUID sí.**

---

## Endpoints

### 1. Onboarding Rápido (Registro)

**POST** `/api/v1/clients`

Crea Account + Organization + User en una sola operación con datos mínimos.

#### Request Body

**Campos obligatorios:**

```json
{
  "account_name": "Mi Empresa S.A.",
  "email": "admin@miempresa.com",
  "password": "SecureP@ss123!"
}
```

**Campos opcionales:**

```json
{
  "account_name": "Mi Empresa S.A.",
  "email": "admin@miempresa.com",
  "password": "SecureP@ss123!",
  "billing_email": "facturacion@miempresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City"
}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `account_name` | string | ✅ | Nombre de la cuenta (puede repetirse) |
| `email` | string | ✅ | Email del usuario master (debe ser único) |
| `password` | string | ✅ | Contraseña (min 8 caracteres) |
| `billing_email` | string | ❌ | Email de facturación (default: email) |
| `country` | string | ❌ | Código ISO 3166-1 alpha-2 (ej: "MX") |
| `timezone` | string | ❌ | Zona horaria IANA (ej: "America/Mexico_City") |

#### Validaciones

| Validación | Resultado |
|------------|-----------|
| ❌ Unicidad de `account_name` | **NO SE VALIDA** |
| ❌ Unicidad global de `organization.name` | **NO SE VALIDA** |
| ✅ Unicidad de `email` | **SE VALIDA** (global) |
| ✅ Formato de email | SE VALIDA |
| ✅ Contraseña mínimo 8 caracteres | SE VALIDA |

#### Response 201 Created

```json
{
  "account_id": "123e4567-e89b-12d3-a456-426614174000",
  "organization_id": "223e4567-e89b-12d3-a456-426614174001",
  "user_id": "323e4567-e89b-12d3-a456-426614174002"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 400 | `"Ya existe un usuario con este correo electrónico."` |
| 422 | Error de validación (contraseña débil, email inválido) |
| 500 | `"Error al registrar usuario: ..."` |

#### Flujo Interno

```
POST /api/v1/clients
        │
        ▼
┌───────────────────────────────────────┐
│ 1. Validar email único                │
│    (ÚNICA validación de unicidad)     │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 2. Crear Account                      │
│    name = account_name                │
│    billing_email = billing_email ?? email
│    status = ACTIVE                    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 3. Crear Organization                 │
│    name = account_name                │
│    account_id = account.id            │
│    status = ACTIVE                    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 4. Crear User                         │
│    email = input.email                │
│    organization_id = organization.id  │
│    is_master = true                   │
│    email_verified = false             │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 5. Crear OrganizationUser             │
│    role = OWNER                       │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 6. Registrar en Cognito               │
│    - Crear usuario                    │
│    - Establecer contraseña            │
│    - Guardar cognito_sub              │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 7. Enviar email verificación          │
│    (NO falla si el envío falla)       │
└───────────────────┬───────────────────┘
                    │
                    ▼
           Response: IDs creados
```

---

### 2. Obtener Organización Actual

**GET** `/api/v1/clients`

Obtiene la información de la organización del usuario autenticado.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "223e4567-e89b-12d3-a456-426614174001",
  "account_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Mi Empresa S.A.",
  "status": "ACTIVE",
  "billing_email": "facturacion@miempresa.com",
  "country": "MX",
  "timezone": "America/Mexico_City",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 404 | `"Organización no encontrada"` |

---

## Perfil Progresivo

Después del onboarding rápido, el usuario puede completar su perfil gradualmente usando:

**PATCH** `/api/v1/accounts/{account_id}`

Ver [documentación de Accounts](./accounts.md) para detalles.

---

## Estados de la Organización

| Estado | Descripción |
|--------|-------------|
| `ACTIVE` | Organización activa y operativa |
| `PENDING` | Pendiente de verificación (legacy) |
| `SUSPENDED` | Suspendida administrativamente |
| `DELETED` | Eliminación lógica |

> **Nota**: En el nuevo flujo, las organizaciones se crean directamente en estado `ACTIVE`.
> El estado `PENDING` es legacy del flujo anterior.

---

## Casos de Uso

### Persona Individual

```json
{
  "account_name": "Juan García",
  "email": "juan@gmail.com",
  "password": "MiContraseña123!"
}
```

### Familia

```json
{
  "account_name": "Familia García López",
  "email": "familia@gmail.com",
  "password": "FamiliaSegura123!"
}
```

### Empresa

```json
{
  "account_name": "Transportes García S.A. de C.V.",
  "email": "admin@transportesgarcia.com",
  "password": "EmpresaSegura123!",
  "billing_email": "facturacion@transportesgarcia.com",
  "country": "MX",
  "timezone": "America/Mexico_City"
}
```

---

## Notas de Seguridad

### Endpoint Público

- **No requiere autenticación**
- Se recomienda rate limiting en producción
- Validación de formato de email
- Contraseña almacenada seguramente en Cognito

### Proceso de Verificación

1. Usuario recibe email de verificación
2. Clic en link de verificación
3. `POST /api/v1/auth/verify-email?token=...`
4. Usuario marcado como `email_verified = true`
5. Puede iniciar sesión normalmente

---

## Referencias

- [API de Accounts](./accounts.md) - Perfil progresivo
- [API de Auth](./auth.md) - Verificación de email y login
- [ADR-001](../architecture/adr/001-account-organization-user-model.md) - Decisión arquitectónica
- [Modelo Organizacional](../guides/organizational-model.md)

---

**Última actualización**: Diciembre 2024
