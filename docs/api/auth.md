# API de Autenticación

## Descripción

Endpoints para gestionar autenticación en SISCOM Admin API. El sistema soporta **autenticación dual**:

| Tipo | Tecnología | Caso de Uso |
|------|------------|-------------|
| **Usuarios** | AWS Cognito (JWT) | Aplicaciones cliente, usuarios finales |
| **Servicios** | PASETO | API interna, panel administrativo (gac-web) |

> **Referencia**: Ver [Modelo Organizacional](../guides/organizational-model.md) para entender roles y permisos.

### Sistema de Roles

Los usuarios tienen roles dentro de su organización que determinan sus permisos:

| Rol | Descripción |
|-----|-------------|
| `owner` | Propietario - permisos totales |
| `admin` | Administrador - gestión de usuarios y config |
| `billing` | Facturación - pagos y suscripciones |
| `member` | Miembro - acceso operativo |

---

## Endpoints

### 1. Registro (Onboarding)

**POST** `/api/v1/auth/register`

Registra una nueva cuenta creando Account + Organization + User en una sola operación.

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
  "name": "Juan Pérez López",
  "organization_name": "Flota Norte",
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
| `name` | string | ❌ | Nombre completo del usuario (default: account_name) |
| `organization_name` | string | ❌ | Nombre de la organización (default: "ORG " + account_name) |
| `billing_email` | string | ❌ | Email de facturación (default: email) |
| `country` | string | ❌ | Código ISO 3166-1 alpha-2 (ej: "MX") |
| `timezone` | string | ❌ | Zona horaria IANA (ej: "America/Mexico_City") |

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
| 409 | `"El usuario con email ... ya existe."` (en Cognito) |
| 422 | Error de validación (contraseña débil, email inválido) |
| 500 | `"No se pudo completar el registro..."` |

#### Flujo Interno

```
POST /api/v1/auth/register
        │
        ▼
┌───────────────────────────────────────┐
│ 1. Validar email único                │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 2. Crear Account (raíz comercial)     │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 3. Crear Organization (raíz operativa)│
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 4. Crear User master                  │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 5. Crear OrganizationUser (OWNER)     │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 6. Registrar en Cognito               │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 7. Enviar email de verificación       │
└───────────────────┬───────────────────┘
                    │
                    ▼
           Response: IDs creados
```

---

### 2. Obtener Mi Cuenta

**GET** `/api/v1/auth/me`

Obtiene el Account del usuario autenticado junto con su rol en la organización actual.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "account": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "account_name": "Mi Empresa S.A.",
    "status": "ACTIVE",
    "billing_email": "facturacion@miempresa.com",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T15:45:00Z"
  },
  "role": "owner",
  "organization_id": "223e4567-e89b-12d3-a456-426614174001"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `account` | object | Información del Account |
| `role` | string | Rol del usuario: `owner`, `admin`, `billing`, `member` |
| `organization_id` | UUID | ID de la organización actual del usuario |

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 404 | `"Organización no encontrada"` / `"Account no encontrado"` |

---

### 3. Login

**POST** `/api/v1/auth/login`

Autentica un usuario y devuelve tokens de acceso.

#### Request Body

```json
{
  "email": "usuario@ejemplo.com",
  "password": "MiPassword123!"
}
```

#### Response 200 OK

```json
{
  "access_token": "eyJhbGciOiJSUzI1...",
  "id_token": "eyJhbGciOiJSUzI1...",
  "refresh_token": "eyJjdHkiOiJKV1Q...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "usuario@ejemplo.com",
  "email_verified": true
}
```

#### Errores Comunes

- **401 Unauthorized**: Credenciales inválidas
- **403 Forbidden**: Email no verificado
- **400 Bad Request**: Formato de email o contraseña inválido

---

### 4. Recuperación de Contraseña - Solicitar Código

**POST** `/api/v1/auth/forgot-password`

Inicia el proceso de recuperación de contraseña. El sistema genera un código de 6 dígitos y lo envía al email del usuario.

#### Request Body

```json
{
  "email": "usuario@ejemplo.com"
}
```

#### Response 200 OK

```json
{
  "message": "Se ha enviado un código de verificación al correo registrado."
}
```

#### Notas

- El código de verificación es de **6 dígitos numéricos** (ej: `123456`)
- El código se envía por correo electrónico
- El código expira en **1 hora**
- Por seguridad, siempre retorna el mismo mensaje, independientemente de si el email existe

---

### 5. Recuperación de Contraseña - Restablecer

**POST** `/api/v1/auth/reset-password`

Restablece la contraseña usando el código de 6 dígitos enviado por email.

#### Request Body

```json
{
  "email": "usuario@ejemplo.com",
  "code": "123456",
  "new_password": "NuevaPassword123!"
}
```

#### Response 200 OK

```json
{
  "message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
}
```

#### Errores Comunes

- **400 Bad Request**: Código inválido o expirado
- **400 Bad Request**: Código ya utilizado
- **400 Bad Request**: Contraseña no cumple requisitos de seguridad
- **404 Not Found**: Usuario no encontrado

---

### 6. Cambiar Contraseña

**PATCH** `/api/v1/auth/password`

Permite a un usuario autenticado cambiar su contraseña.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "old_password": "MiPasswordActual123!",
  "new_password": "MiNuevoPassword456!"
}
```

#### Response 200 OK

```json
{
  "message": "Contraseña cambiada exitosamente.",
  "email": "usuario@ejemplo.com"
}
```

#### Errores Comunes

- **401 Unauthorized**: Token inválido o expirado
- **403 Forbidden**: Email no verificado
- **400 Bad Request**: Contraseña actual incorrecta
- **400 Bad Request**: Nueva contraseña no cumple requisitos

---

### 7. Cerrar Sesión (Logout)

**POST** `/api/v1/auth/logout`

Cierra la sesión del usuario actual invalidando todos sus tokens en AWS Cognito.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "message": "Sesión cerrada exitosamente."
}
```

#### Errores Comunes

- **401 Unauthorized**: Token inválido o expirado
- **500 Internal Server Error**: Error al cerrar sesión en Cognito

#### Notas

- Este endpoint invalida **todos** los tokens del usuario:
  - Todos los access tokens
  - Todos los ID tokens
  - Los refresh tokens ya no podrán usarse
- Después del logout, el usuario deberá volver a iniciar sesión
- El cliente debe eliminar los tokens del almacenamiento local después de llamar a este endpoint

---

### 8. Renovar Tokens (Refresh)

**POST** `/api/v1/auth/refresh`

Renueva el access token y el id token usando un refresh token válido.

#### Request Body

```json
{
  "refresh_token": "eyJjdHkiOiJKV1Q..."
}
```

#### Response 200 OK

```json
{
  "access_token": "eyJhbGciOiJSUzI1...",
  "id_token": "eyJhbGciOiJSUzI1...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

#### Errores Comunes

- **401 Unauthorized**: Refresh token inválido o expirado
- **400 Bad Request**: Parámetros inválidos
- **500 Internal Server Error**: Error al renovar el token en Cognito

#### Notas

- Este endpoint **NO requiere autenticación** (es público)
- El refresh token NO se renueva, sigue siendo el mismo
- Solo se renuevan el access token y el id token
- Use este endpoint cuando el access token expire para evitar que el usuario tenga que iniciar sesión nuevamente
- El refresh token tiene una duración mayor (típicamente 30 días)

---

### 9. Generar Token Interno (PASETO)

**POST** `/api/v1/auth/internal`

Genera un token PASETO para autenticación de servicios internos. Este token permite a servicios externos autenticarse en la API sin necesidad de un usuario de Cognito.

---

## ⛔ ADVERTENCIA CRÍTICA DE SEGURIDAD ⛔

> ### 🚨 NUNCA EXPONER ESTE ENDPOINT PÚBLICAMENTE 🚨
>
> Este endpoint genera tokens que contienen el **email del usuario** y se utilizan para:
> - Identificar quién ejecuta comandos en dispositivos (`request_user_email`)
> - Autenticar servicios internos sin validación de credenciales
>
> ### Riesgos si se expone públicamente:
> - **Suplantación de identidad**: Cualquiera puede generar tokens con cualquier email
> - **Acceso no autorizado**: Los tokens permiten ejecutar comandos en dispositivos
> - **Sin auditoría confiable**: Los logs mostrarán emails falsos
>
> ### Medidas obligatorias:
> 1. **NUNCA** hacer público `gac-admin` ni ninguna aplicación que use este endpoint
> 2. Proteger con **firewall** que solo permita IPs de servicios autorizados
> 3. Usar **VPN** o **red privada** para comunicación entre servicios
> 4. Implementar **API Gateway** con políticas de acceso restrictivas
> 5. **Auditar** regularmente los accesos a este endpoint

---

#### Request Body

```json
{
  "email": "usuario@ejemplo.com",
  "service": "gac",
  "role": "NEXUS_ADMIN",
  "expires_in_hours": 24
}
```

#### Campos del Request

| Campo             | Tipo   | Requerido | Descripción                                        |
| ----------------- | ------ | --------- | -------------------------------------------------- |
| `email`           | string | Sí        | Email del usuario que solicita el token            |
| `service`         | string | Sí        | Nombre del servicio (ej: "gac")                    |
| `role`            | string | Sí        | Rol del servicio (ej: "NEXUS_ADMIN")               |
| `expires_in_hours`| int    | No        | Horas de validez del token (default: 24, max: 720) |

#### Response 200 OK

```json
{
  "token": "v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4...",
  "expires_at": "2024-01-16T10:30:00Z",
  "token_type": "Bearer"
}
```

#### Contenido del Token (Payload)

El token PASETO generado contiene la siguiente información:

```json
{
  "token_id": "550e8400-e29b-41d4-a716-446655440000",
  "service": "gac",
  "role": "NEXUS_ADMIN",
  "scope": "internal-nexus-admin",
  "email": "usuario@ejemplo.com",
  "iat": "2024-01-15T10:30:00Z",
  "exp": "2024-01-16T10:30:00Z"
}
```

| Campo      | Descripción                                    |
| ---------- | ---------------------------------------------- |
| `token_id` | UUID único del token                           |
| `service`  | Nombre del servicio                            |
| `role`     | Rol asignado al servicio                       |
| `scope`    | Alcance del token (`internal-nexus-admin`)     |
| `email`    | Email del usuario que solicitó el token        |
| `iat`      | Fecha de emisión (issued at)                   |
| `exp`      | Fecha de expiración                            |

#### Ejemplo Completo

**1. Obtener el token:**

```bash
curl -X POST http://api.example.com/api/v1/auth/internal \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "service": "gac",
    "role": "NEXUS_ADMIN",
    "expires_in_hours": 24
  }'
```

**2. Usar el token en endpoints protegidos:**

```bash
curl -X POST http://api.example.com/api/v1/commands \
  -H "Authorization: Bearer v4.local.VGhpcyBpcyBhIHRlc3QgdG9rZW4..." \
  -H "Content-Type: application/json" \
  -d '{"command": "AT+LOCATION", "media": "sms", "device_id": "123456"}'
```

#### Endpoints que Aceptan Tokens PASETO

Los siguientes endpoints aceptan autenticación dual (Cognito o PASETO):

| Endpoint                                        | Servicio Requerido | Rol Requerido |
| ----------------------------------------------- | ------------------ | ------------- |
| `POST /api/v1/commands`                         | gac                | NEXUS_ADMIN   |
| `GET /api/v1/commands/{command_id}`             | gac                | NEXUS_ADMIN   |
| `GET /api/v1/commands/device/{id}`              | gac                | NEXUS_ADMIN   |
| `POST /api/v1/devices`                          | gac                | NEXUS_ADMIN   |
| `PATCH /api/v1/devices/{device_id}`             | gac                | NEXUS_ADMIN   |
| `GET /api/v1/internal/organizations`                  | gac                | NEXUS_ADMIN   |
| `GET /api/v1/internal/organizations/stats`            | gac                | NEXUS_ADMIN   |
| `GET /api/v1/internal/organizations/{org_id}`         | gac                | NEXUS_ADMIN   |
| `GET /api/v1/internal/organizations/{org_id}/users`   | gac                | NEXUS_ADMIN   |
| `PATCH /api/v1/internal/organizations/{org_id}/status`| gac                | NEXUS_ADMIN   |

#### Notas de Seguridad

- **⚠️ Importante**: Este endpoint debe estar protegido en producción mediante:
  - Reglas de firewall que limiten el acceso solo a servicios autorizados
  - API Gateway con políticas de acceso
  - VPN o red privada
- El token generado tiene acceso completo según el rol especificado
- Los tokens PASETO son firmados simétricamente usando la clave `PASETO_SECRET_KEY`
- No se requiere autenticación para llamar a este endpoint (debe protegerse externamente)

---

### 10. Reenviar Verificación de Email

**POST** `/api/v1/auth/resend-verification`

Reenvía el correo de verificación de email a un usuario no verificado. Este endpoint funciona tanto para usuarios master como para usuarios normales.

#### Request Body

```json
{
  "email": "usuario@ejemplo.com"
}
```

#### Response 200 OK

```json
{
  "message": "Si la cuenta existe, se ha reenviado el correo de verificación."
}
```

#### Notas Importantes

- **Usuarios Master**: El sistema reutiliza la misma contraseña temporal generada al crear el cliente. Esto permite reenviar la verificación múltiples veces sin perder la contraseña original.
- **Usuarios Normales**: Se genera un token de verificación sin contraseña temporal.
- **Seguridad**: Siempre retorna el mismo mensaje sin revelar si el usuario existe o ya está verificado.
- El token de verificación expira en **24 horas**.
- Los tokens anteriores no usados se invalidan automáticamente.
- El usuario puede solicitar reenvío múltiples veces sin problemas.

#### Flujo de Reutilización de Contraseña (Usuarios Master)

1. Al crear un cliente, se genera `password_temp` con la contraseña proporcionada
2. Si el usuario solicita reenvío, el sistema busca el `password_temp` del token más reciente
3. El nuevo token reutiliza exactamente la misma `password_temp`
4. Esto garantiza que la contraseña funcione sin importar cuántas veces se reenvíe
5. Solo al verificar exitosamente, se elimina la `password_temp` de forma permanente

---

### 11. Verificar Email

**POST** `/api/v1/auth/verify-email`

Verifica el email de un usuario utilizando un token de verificación. Este endpoint unificado maneja tanto usuarios master como usuarios normales.

#### Query Parameters

- `token` (string, requerido): Token de verificación recibido por email

#### Ejemplo de Petición

```bash
POST /api/v1/auth/verify-email?token=abc123def456ghi789
```

#### Response 200 OK

```json
{
  "message": "Email verificado exitosamente. Tu cuenta ha sido activada y ahora puedes iniciar sesión."
}
```

#### Errores Comunes

- **400 Bad Request**: Token inválido, expirado o ya usado
- **400 Bad Request**: Email ya verificado
- **400 Bad Request**: Token inválido para usuarios master (sin password_temp)
- **404 Not Found**: Usuario o cliente no encontrado
- **500 Internal Server Error**: Error al configurar usuario en Cognito

#### Flujos de Verificación

##### FLUJO A - Usuario Master con password_temp

Para usuarios master (is_master=True) que tienen un token con contraseña temporal:

1. Busca y valida el token de verificación
2. Verifica que no esté expirado ni usado
3. Busca el usuario y el cliente asociados
4. Si el usuario no existe en Cognito:
   - Crea el usuario en AWS Cognito con email verificado
   - Establece la contraseña usando `password_temp`
5. Si el usuario ya existe en Cognito:
   - Actualiza la contraseña usando `password_temp`
   - Marca el email como verificado
6. Actualiza el usuario local:
   - Asigna `cognito_sub` del usuario de Cognito
   - Marca `email_verified = True`
7. Activa el cliente (`status = ACTIVE`)
8. Marca el token como usado
9. **Elimina** `password_temp` permanentemente por seguridad

##### FLUJO B - Usuario Master sin password_temp (Token Inválido)

Si un usuario master tiene un token sin `password_temp`:

- Retorna error: "Token inválido para usuarios master. Por favor, solicita un nuevo enlace de verificación."
- Este caso solo ocurre con tokens antiguos o corruptos
- El usuario debe solicitar reenvío de verificación

##### FLUJO C - Usuario Normal (no master)

Para usuarios normales (is_master=False):

1. Busca y valida el token de verificación
2. Verifica que no esté expirado ni usado
3. Marca el email como verificado en la base de datos local
4. Marca el token como usado
5. **NO** crea usuario en Cognito (debe existir previamente)
6. **NO** asigna contraseña
7. **NO** modifica el estado del cliente

---

## Requisitos de Contraseña

Las contraseñas deben cumplir con los siguientes requisitos de AWS Cognito:

- Mínimo 8 caracteres
- Al menos una letra mayúscula
- Al menos una letra minúscula
- Al menos un número
- Al menos un carácter especial (!@#$%^&\*)

---

## Flujo de Uso del Refresh Token

El refresh token permite mantener al usuario autenticado sin que tenga que volver a ingresar sus credenciales:

1. Usuario inicia sesión con `POST /api/v1/auth/login`
2. El sistema retorna `access_token`, `id_token` y `refresh_token`
3. Cliente almacena los tres tokens de forma segura
4. Cliente usa el `access_token` para llamadas a endpoints protegidos
5. Cuando el `access_token` expira (después de 1 hora):
   - Cliente detecta error 401 en una llamada protegida
   - Cliente llama a `POST /api/v1/auth/refresh` con el `refresh_token`
   - Sistema retorna nuevos `access_token` e `id_token`
   - Cliente actualiza los tokens almacenados
   - Cliente reintenta la llamada fallida con el nuevo `access_token`
6. El `refresh_token` permanece válido hasta que:
   - Expire (típicamente 30 días)
   - El usuario haga logout (`POST /api/v1/auth/logout`)
   - Se revoque manualmente en Cognito

**Mejores prácticas:**

- Almacenar el refresh token de forma segura (nunca en localStorage en aplicaciones web)
- Implementar renovación automática de tokens antes de que expiren
- Manejar el caso cuando el refresh token también expira (redirigir a login)

---

## Flujo Completo de Recuperación de Contraseña

1. Usuario hace clic en "Olvidé mi contraseña" en el frontend
2. Frontend llama a `POST /api/v1/auth/forgot-password` con el email
3. **Backend genera un código de 6 dígitos** y lo envía por correo electrónico
4. Usuario recibe el email con el **código numérico de 6 dígitos** (ej: `123456`)
5. Usuario ingresa el código y nueva contraseña en el frontend
6. Frontend llama a `POST /api/v1/auth/reset-password` con email, código y nueva contraseña
7. Sistema valida el código y actualiza la contraseña en AWS Cognito
8. Usuario puede iniciar sesión con la nueva contraseña

---

## Flujo Completo de Verificación de Email

### Para Usuarios Master (Creación de Cliente)

1. Usuario se registra con `POST /api/v1/auth/register` (nombre, email, password)
2. Sistema crea:
   - Cliente en estado `PENDING`
   - Usuario master con `email_verified=False`
   - Token con `password_temp` (guarda la contraseña proporcionada)
3. Usuario recibe email con link de verificación
4. Usuario hace clic en el link → `POST /api/v1/auth/verify-email?token=...`
5. Sistema:
   - Crea usuario en AWS Cognito
   - Establece la contraseña usando `password_temp`
   - Activa el cliente (`ACTIVE`)
   - Elimina `password_temp`
6. Usuario puede hacer login con su contraseña

### Si el Usuario Master No Recibe el Email

1. Usuario solicita reenvío → `POST /api/v1/auth/resend-verification`
2. Sistema:
   - Busca el `password_temp` del token más reciente
   - **Reutiliza** la misma contraseña temporal (no genera una nueva)
   - Crea nuevo token con el mismo `password_temp`
   - Envía nuevo email
3. Usuario puede reenviar cuantas veces necesite
4. La contraseña siempre será la misma hasta que verifique

### Para Usuarios Normales (Invitados)

1. Usuario master invita a otro usuario
2. Sistema crea usuario y envía token de verificación (sin `password_temp`)
3. Usuario verifica email → `POST /api/v1/auth/verify-email?token=...`
4. Sistema solo marca `email_verified=True` (no toca Cognito)

---

## Notas de Seguridad

### Tokens Cognito

- Los tokens de acceso expiran en 1 hora
- Los tokens de verificación de email expiran en 24 horas
- Los códigos de recuperación de contraseña expiran en 1 hora
- Los códigos son de 6 dígitos numéricos y se pueden usar solo una vez
- El refresh token puede usarse para obtener nuevos access tokens sin reautenticar
- Los refresh tokens tienen una duración mayor (típicamente 30 días)
- **Contraseñas temporales**: Se reutilizan en reenvíos para usuarios master, nunca se envían por correo, solo se usan internamente para Cognito

### Tokens PASETO (Servicios Internos)

- Los tokens PASETO son para autenticación de servicios internos (server-to-server)
- Se generan con `POST /api/v1/auth/internal`
- Expiran según el parámetro `expires_in_hours` (default: 24 horas, máximo: 720 horas)
- Usan cifrado simétrico (PASETO v4.local) con la clave `PASETO_SECRET_KEY`
- Requieren `service` y `role` específicos para acceder a endpoints protegidos
- El endpoint `/internal` debe protegerse externamente (firewall, API Gateway, VPN)

### Clasificación de Endpoints

| Tipo | Endpoints |
|------|-----------|
| **Públicos** (sin autenticación) | login, forgot-password, reset-password, resend-verification, verify-email, refresh, internal, accept-invitation |
| **Protegidos** (requieren Cognito) | password (cambiar contraseña), logout |
| **Duales** (Cognito o PASETO) | commands, devices (crear/actualizar), internal/organizations |

### Permisos por Rol en Endpoints Protegidos

| Endpoint | owner | admin | billing | member |
|----------|:-----:|:-----:|:-------:|:------:|
| `GET /users/` | ✅ | ✅ | ❌ | ❌ |
| `POST /users/invite` | ✅ | ✅ | ❌ | ❌ |
| `GET /payments/` | ✅ | ❌ | ✅ | ❌ |
| `GET /subscriptions/` | ✅ | ✅ | ✅ | ❌ |
| `GET /devices/` (todos) | ✅ | ✅ | ❌ | ❌ |
| `GET /units/` (asignadas) | ✅ | ✅ | ❌ | ✅ |

### Mejores Prácticas

- Por seguridad, los endpoints forgot-password y resend-verification siempre retornan el mismo mensaje sin revelar si el email existe
- El endpoint `/internal` debe protegerse a nivel de infraestructura (no exponer públicamente)
- Los tokens PASETO deben almacenarse de forma segura en los servicios que los usen
- Usar tiempos de expiración cortos para tokens PASETO en ambientes de producción
- Validar el rol del usuario antes de permitir operaciones sensibles
- Los usuarios `member` solo deben ver recursos que les han sido asignados explícitamente

---

## Información del Token y Organización

### Contenido del Token Cognito

El token JWT de Cognito contiene:

```json
{
  "sub": "cognito-sub-uuid",
  "email": "usuario@ejemplo.com",
  "email_verified": true,
  "custom:client_id": "organization-uuid"
}
```

### Resolución de Permisos

```
Token JWT
    ↓
Extraer cognito_sub
    ↓
Buscar User por cognito_sub
    ↓
Obtener organization_id (client_id)
    ↓
Obtener rol de organization_users
    ↓
Validar permiso según rol
    ↓
Filtrar datos por organization_id
```

### Información Disponible en /users/me

```json
{
  "id": "user-uuid",
  "email": "usuario@ejemplo.com",
  "full_name": "Nombre Usuario",
  "role": "admin",
  "is_master": true,
  "organization_id": "org-uuid",
  "permissions": {
    "can_invite_users": true,
    "can_manage_billing": false,
    "can_view_all_devices": true,
    "can_manage_organization": true
  }
}
```

---

**Última actualización**: Diciembre 2025  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)
