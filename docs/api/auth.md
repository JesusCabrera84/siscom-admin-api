# API de Autenticación

## Descripción

Endpoints para gestionar autenticación de usuarios con AWS Cognito, incluyendo login, renovación de tokens, recuperación de contraseña, cambio de contraseña y verificación de email.

---

## Endpoints

### 1. Login

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

### 2. Recuperación de Contraseña - Solicitar Código

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

### 3. Recuperación de Contraseña - Restablecer

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

### 4. Cambiar Contraseña

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
- **400 Bad Request**: Contraseña actual incorrecta
- **400 Bad Request**: Nueva contraseña no cumple requisitos

---

### 5. Cerrar Sesión (Logout)

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

### 6. Renovar Tokens (Refresh)

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

### 7. Reenviar Verificación de Email

**POST** `/api/v1/auth/resend-verification`

Reenvía el código de verificación al email del usuario.

#### Request Body

```json
{
  "email": "usuario@ejemplo.com"
}
```

#### Response 200 OK

```json
{
  "message": "Si el email existe y no está verificado, recibirás un nuevo código.",
  "email": "usuario@ejemplo.com"
}
```

---

### 8. Confirmar Email

**POST** `/api/v1/auth/confirm-email`

Confirma el email del usuario usando el código enviado.

#### Request Body

```json
{
  "email": "usuario@ejemplo.com",
  "code": "123456"
}
```

#### Response 200 OK

```json
{
  "message": "Email verificado exitosamente. Ahora puedes iniciar sesión.",
  "email": "usuario@ejemplo.com"
}
```

#### Errores Comunes

- **400 Bad Request**: Código inválido o expirado
- **400 Bad Request**: Email ya verificado

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

## Notas de Seguridad

- Los tokens de acceso expiran en 1 hora
- Los códigos de verificación de email expiran en 24 horas
- Los códigos de recuperación de contraseña expiran en 1 hora
- Los códigos son de 6 dígitos numéricos y se pueden usar solo una vez
- El refresh token puede usarse para obtener nuevos access tokens sin reautenticar
- Los refresh tokens tienen una duración mayor (típicamente 30 días)
- Los endpoints públicos (no requieren autenticación): login, forgot-password, reset-password, resend-verification, confirm-email, refresh
- Los endpoints protegidos (requieren autenticación): password (cambiar contraseña), logout
- Por seguridad, los endpoints forgot-password y resend-verification siempre retornan el mismo mensaje sin revelar si el email existe
