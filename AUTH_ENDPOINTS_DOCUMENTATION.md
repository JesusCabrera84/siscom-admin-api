# Documentación de Endpoints de Autenticación

Esta guía documenta todos los endpoints de autenticación disponibles en la API.

## 📋 Índice

1. [Cambiar Contraseña (Usuario Autenticado)](#1-cambiar-contraseña-usuario-autenticado)
2. [Reenviar Verificación de Email](#2-reenviar-verificación-de-email)
3. [Confirmar Email](#3-confirmar-email)

---

## 1. Cambiar Contraseña (Usuario Autenticado)

### `PATCH /api/v1/auth/password`

Permite a un usuario autenticado cambiar su propia contraseña. Requiere proporcionar la contraseña actual y la nueva contraseña.

### 🔒 Autenticación Requerida

Este endpoint requiere un token de acceso válido en el header `Authorization`.

```
Authorization: Bearer <access_token>
```

### Request

**Headers:**
```
Content-Type: application/json
Authorization: Bearer eyJraWQiOiJ...
```

**Body:**
```json
{
  "old_password": "MiPwdAnterior123",
  "new_password": "NuevoPwdFuerte456!"
}
```

### Response

**Success (200 OK):**
```json
{
  "message": "Contraseña actualizada exitosamente."
}
```

**Errors:**

- **400 Bad Request** - Contraseña actual incorrecta:
```json
{
  "detail": "La contraseña actual es incorrecta"
}
```

- **400 Bad Request** - Nueva contraseña inválida:
```json
{
  "detail": "La nueva contraseña no cumple con los requisitos: ..."
}
```

- **401 Unauthorized** - Token inválido o expirado:
```json
{
  "detail": "Invalid token"
}
```

### Proceso Interno

1. ✅ Verifica que el usuario esté autenticado (valida Bearer token)
2. ✅ Autentica con Cognito usando la contraseña actual para verificarla
3. ✅ Si la contraseña actual es correcta, actualiza la contraseña en Cognito
4. ✅ Usa `AdminSetUserPassword` para establecer la nueva contraseña
5. ✅ Retorna mensaje de éxito

### Validaciones

La nueva contraseña debe cumplir con:
- ✅ Mínimo 8 caracteres
- ✅ Al menos una letra mayúscula (A-Z)
- ✅ Al menos una letra minúscula (a-z)
- ✅ Al menos un número (0-9)
- ✅ Al menos un carácter especial (!@#$%^&*(),.?":{}|<>)

### Ejemplos de Uso

#### cURL
```bash
curl -X PATCH http://localhost:8000/api/v1/auth/password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJraWQiOiJ..." \
  -d '{
    "old_password": "MiPwdAnterior123",
    "new_password": "NuevoPwdFuerte456!"
  }'
```

#### Python
```python
import requests

url = "http://localhost:8000/api/v1/auth/password"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJraWQiOiJ..."
}
data = {
    "old_password": "MiPwdAnterior123",
    "new_password": "NuevoPwdFuerte456!"
}

response = requests.patch(url, json=data, headers=headers)
print(response.json())
```

#### JavaScript/Axios
```javascript
const axios = require('axios');

const response = await axios.patch(
  'http://localhost:8000/api/v1/auth/password',
  {
    old_password: 'MiPwdAnterior123',
    new_password: 'NuevoPwdFuerte456!'
  },
  {
    headers: {
      'Authorization': 'Bearer eyJraWQiOiJ...'
    }
  }
);

console.log(response.data);
```

### Notas de Seguridad

- ✅ El usuario debe estar autenticado (token válido)
- ✅ La contraseña actual se verifica antes de cambiarla
- ✅ La nueva contraseña se valida contra los requisitos de seguridad
- ✅ Los cambios se realizan directamente en AWS Cognito
- ✅ Se registra en logs cada cambio de contraseña para auditoría

---

## 2. Reenviar Verificación de Email

### `POST /api/v1/auth/resend-verification`

Reenvía el correo de verificación a un usuario que no ha verificado su email.

### 🔓 Sin Autenticación

Este endpoint no requiere autenticación.

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "email": "usuario@example.com"
}
```

### Response

**Success (200 OK):**
```json
{
  "message": "Si la cuenta existe, se ha reenviado el correo de verificación."
}
```

> **Nota:** Este endpoint siempre retorna el mismo mensaje, sin revelar si el usuario existe o ya está verificado (medida de seguridad).

### Proceso Interno

1. ✅ Busca el usuario por email en la base de datos
2. ✅ Si no existe → retorna mensaje genérico (no revela que no existe)
3. ✅ Si ya está verificado → retorna mensaje genérico (no revela que ya está verificado)
4. ✅ Si existe y no está verificado:
   - Invalida todos los tokens de verificación anteriores no usados
   - Genera un nuevo token UUID
   - Guarda el token en `tokens_confirmacion` con tipo `EMAIL_VERIFICATION`
   - Expira en 24 horas
   - ⏳ TODO: Envía correo con el token
5. ✅ Retorna mensaje genérico

### Ejemplos de Uso

#### cURL
```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com"
  }'
```

#### Python
```python
import requests

url = "http://localhost:8000/api/v1/auth/resend-verification"
data = {"email": "usuario@example.com"}

response = requests.post(url, json=data)
print(response.json())
```

#### JavaScript/Axios
```javascript
const axios = require('axios');

const response = await axios.post(
  'http://localhost:8000/api/v1/auth/resend-verification',
  {
    email: 'usuario@example.com'
  }
);

console.log(response.data);
```

### Comportamiento por Caso

| Caso | Comportamiento | Mensaje Retornado |
|------|----------------|-------------------|
| Usuario no existe | No hace nada | "Si la cuenta existe, se ha reenviado..." |
| Usuario ya verificado | No hace nada | "Si la cuenta existe, se ha reenviado..." |
| Usuario no verificado | Genera nuevo token e invalida anteriores | "Si la cuenta existe, se ha reenviado..." |

### Notas de Seguridad

- ✅ No revela si el usuario existe o no (respuesta consistente)
- ✅ No revela si el usuario ya está verificado
- ✅ Invalida tokens anteriores al generar uno nuevo
- ✅ Tokens expiran en 24 horas
- ✅ Se registra en logs para auditoría

### TODO

- ⏳ Implementar envío de correo electrónico con el token
- ⏳ Crear plantilla HTML para el correo de verificación

---

## 3. Confirmar Email

### `POST /api/v1/auth/confirm-email`

Confirma el email de un usuario utilizando el token de verificación enviado por correo.

### 🔓 Sin Autenticación

Este endpoint no requiere autenticación.

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "token": "abc123-def456-ghi789"
}
```

### Response

**Success (200 OK):**
```json
{
  "message": "Email verificado exitosamente. Ahora puede iniciar sesión."
}
```

**Errors:**

- **400 Bad Request** - Token inválido:
```json
{
  "detail": "Token de verificación inválido"
}
```

- **400 Bad Request** - Token expirado:
```json
{
  "detail": "El token de verificación ha expirado. Por favor, solicita un nuevo código."
}
```

- **400 Bad Request** - Token ya usado:
```json
{
  "detail": "Este token de verificación ya ha sido utilizado"
}
```

- **404 Not Found** - Usuario no encontrado:
```json
{
  "detail": "Usuario no encontrado"
}
```

### Proceso Interno

1. ✅ Busca el token en `tokens_confirmacion` con tipo `EMAIL_VERIFICATION`
2. ✅ Verifica que el token no haya expirado (24 horas)
3. ✅ Verifica que el token no haya sido usado
4. ✅ Busca el usuario asociado al token
5. ✅ Marca el token como usado (`used = True`)
6. ✅ Actualiza `user.email_verified = True`
7. ✅ Retorna mensaje de éxito

### Ejemplos de Uso

#### cURL
```bash
curl -X POST http://localhost:8000/api/v1/auth/confirm-email \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123-def456-ghi789"
  }'
```

#### Python
```python
import requests

url = "http://localhost:8000/api/v1/auth/confirm-email"
data = {"token": "abc123-def456-ghi789"}

response = requests.post(url, json=data)
print(response.json())
```

#### JavaScript/Axios
```javascript
const axios = require('axios');

const response = await axios.post(
  'http://localhost:8000/api/v1/auth/confirm-email',
  {
    token: 'abc123-def456-ghi789'
  }
);

console.log(response.data);
```

### Obtener Token (Temporal)

Mientras no esté implementado el servicio de correos, el token se puede obtener:

**Desde logs:**
```bash
docker-compose logs api | grep "RESEND VERIFICATION"
```

**Desde base de datos:**
```bash
docker-compose exec db psql -U postgres -d siscom_db -c \
  "SELECT token FROM tokens_confirmacion 
   WHERE type='email_verification' 
   AND used=false 
   ORDER BY created_at DESC 
   LIMIT 1;"
```

### Flujo Completo de Verificación

```
1. Usuario se registra
   ↓
2. Sistema genera token de verificación
   ↓
3. (TODO) Sistema envía email con token
   ↓
4. Usuario no recibe el correo o lo perdió
   ↓
5. POST /api/v1/auth/resend-verification
   { "email": "usuario@example.com" }
   ↓
6. Sistema invalida token anterior y genera nuevo
   ↓
7. (TODO) Sistema envía nuevo email con token
   ↓
8. Usuario recibe el token
   ↓
9. POST /api/v1/auth/confirm-email
   { "token": "abc123-..." }
   ↓
10. Sistema marca email_verified = True
   ↓
11. Usuario puede hacer login
```

---

## 📊 Resumen de Endpoints

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/auth/password` | PATCH | ✅ Sí | Cambiar contraseña (usuario autenticado) |
| `/auth/resend-verification` | POST | ❌ No | Reenviar email de verificación |
| `/auth/confirm-email` | POST | ❌ No | Confirmar email con token |

---

## 🔒 Códigos de Estado HTTP

| Código | Descripción | Cuándo |
|--------|-------------|--------|
| 200 | OK | Operación exitosa |
| 400 | Bad Request | Token/contraseña inválido, expirado o ya usado |
| 401 | Unauthorized | Token de autenticación inválido |
| 404 | Not Found | Usuario no encontrado |
| 422 | Unprocessable Entity | Error de validación de datos |
| 500 | Internal Server Error | Error del servidor o Cognito |

---

## 🧪 Casos de Prueba

### Cambiar Contraseña

```bash
# 1. Login para obtener access_token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "PasswordActual123!"}' \
  | jq -r '.access_token')

# 2. Cambiar contraseña
curl -X PATCH http://localhost:8000/api/v1/auth/password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "old_password": "PasswordActual123!",
    "new_password": "NuevoPassword456!"
  }'

# 3. Login con nueva contraseña
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "NuevoPassword456!"}'
```

### Reenvío y Confirmación de Email

```bash
# 1. Reenviar verificación
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com"}'

# 2. Obtener token de BD
TOKEN=$(docker-compose exec db psql -U postgres -d siscom_db -t -c \
  "SELECT token FROM tokens_confirmacion 
   WHERE type='email_verification' AND used=false 
   ORDER BY created_at DESC LIMIT 1;" | tr -d ' ')

# 3. Confirmar email
curl -X POST http://localhost:8000/api/v1/auth/confirm-email \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\"}"
```

---

## 🔐 Consideraciones de Seguridad

### Cambiar Contraseña
- ✅ Requiere autenticación
- ✅ Verifica contraseña actual antes de cambiar
- ✅ Valida nueva contraseña contra requisitos de seguridad
- ✅ Logs de auditoría

### Reenviar Verificación
- ✅ Respuesta consistente (no revela usuarios)
- ✅ Invalida tokens anteriores
- ✅ Tokens con expiración
- ✅ Logs de intentos

### Confirmar Email
- ✅ Tokens de uso único
- ✅ Validación de expiración
- ✅ Validación de uso previo
- ✅ Actualización atómica en BD

---

## ⏳ Pendientes (TODO)

1. **Servicio de Notificaciones:**
   - Implementar envío de correos
   - Crear plantillas HTML para emails
   - Integrar con reenvío de verificación

2. **Mejoras Opcionales:**
   - Rate limiting para prevenir abuso
   - Tests automatizados
   - Notificaciones de cambio de contraseña
   - Dashboard de auditoría

---

**Fecha de actualización:** 4 de noviembre de 2025  
**Versión:** 1.0.0  
**Estado:** ✅ Implementado (pendiente servicio de correos)

