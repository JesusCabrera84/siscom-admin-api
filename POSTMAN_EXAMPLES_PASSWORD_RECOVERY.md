# Ejemplos de Postman - Recuperación de Contraseña

Este documento contiene ejemplos listos para usar en Postman o cualquier cliente REST para probar el sistema de recuperación de contraseña.

## Variables de Entorno (Postman)

Crea estas variables en tu entorno de Postman:

```
base_url = http://localhost:8000
api_version = /api/v1
```

## 1. Solicitar Recuperación de Contraseña

### Request

**Method:** `POST`  
**URL:** `{{base_url}}{{api_version}}/auth/forgot-password`  
**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
  "email": "usuario@example.com"
}
```

### Response Esperada (200 OK)

```json
{
  "message": "Se ha enviado un código de verificación al correo registrado."
}
```

### Casos de Prueba

#### ✅ Caso 1: Usuario existente
```json
{
  "email": "usuario@example.com"
}
```
**Resultado:** Genera token y responde con mensaje de éxito

#### ✅ Caso 2: Usuario no existente
```json
{
  "email": "noexiste@example.com"
}
```
**Resultado:** Responde con el mismo mensaje (por seguridad, no revela que el usuario no existe)

#### ❌ Caso 3: Email inválido
```json
{
  "email": "email-invalido"
}
```
**Resultado:** Error de validación (422 Unprocessable Entity)

---

## 2. Restablecer Contraseña con Token

### Request

**Method:** `POST`  
**URL:** `{{base_url}}{{api_version}}/auth/reset-password`  
**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
  "token": "abc123-def456-ghi789",
  "new_password": "NuevaPassword123!"
}
```

### Response Esperada (200 OK)

```json
{
  "message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
}
```

### Casos de Prueba

#### ✅ Caso 1: Token válido
```json
{
  "token": "TOKEN_GENERADO_EN_BD",
  "new_password": "NuevaPassword123!"
}
```
**Resultado:** Actualiza la contraseña en Cognito y marca el token como usado

#### ❌ Caso 2: Token inválido
```json
{
  "token": "token-invalido-123",
  "new_password": "NuevaPassword123!"
}
```
**Response (400 Bad Request):**
```json
{
  "detail": "Token de recuperación inválido"
}
```

#### ❌ Caso 3: Token expirado
```json
{
  "token": "TOKEN_EXPIRADO",
  "new_password": "NuevaPassword123!"
}
```
**Response (400 Bad Request):**
```json
{
  "detail": "El token de recuperación ha expirado. Por favor, solicita uno nuevo."
}
```

#### ❌ Caso 4: Token ya usado
```json
{
  "token": "TOKEN_YA_USADO",
  "new_password": "NuevaPassword123!"
}
```
**Response (400 Bad Request):**
```json
{
  "detail": "Este token de recuperación ya ha sido utilizado"
}
```

#### ❌ Caso 5: Contraseña inválida (muy corta)
```json
{
  "token": "TOKEN_VALIDO",
  "new_password": "123"
}
```
**Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "new_password"],
      "msg": "String should have at least 8 characters",
      "input": "123",
      "ctx": {
        "min_length": 8
      }
    }
  ]
}
```

#### ❌ Caso 6: Contraseña sin mayúsculas
```json
{
  "token": "TOKEN_VALIDO",
  "new_password": "password123!"
}
```
**Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "new_password"],
      "msg": "Value error, La contraseña debe contener al menos una letra mayúscula",
      "input": "password123!",
      "ctx": {
        "error": {}
      }
    }
  ]
}
```

---

## 3. Login con Nueva Contraseña

### Request

**Method:** `POST`  
**URL:** `{{base_url}}{{api_version}}/auth/login`  
**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
  "email": "usuario@example.com",
  "password": "NuevaPassword123!"
}
```

### Response Esperada (200 OK)

```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@example.com",
    "full_name": "Juan García",
    "is_master": true,
    "email_verified": true,
    "client_id": "223e4567-e89b-12d3-a456-426614174000",
    "cognito_sub": "us-east-1:12345678-1234-1234-1234-123456789012",
    "last_login_at": "2025-11-04T10:30:00Z",
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2025-11-04T10:30:00Z"
  },
  "access_token": "eyJraWQiOiJ...",
  "id_token": "eyJraWQiOiJ...",
  "refresh_token": "eyJjdHkiOiJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

## Colección Completa de Postman

### Flujo Completo de Recuperación

**1. Forgot Password**
```
POST {{base_url}}{{api_version}}/auth/forgot-password
Body:
{
  "email": "usuario@example.com"
}
```

**2. [Obtener Token de BD o Logs]**
```sql
-- Consultar en base de datos
SELECT token, email, expires_at, used 
FROM tokens_confirmacion 
WHERE type = 'password_reset' 
  AND email = 'usuario@example.com' 
ORDER BY created_at DESC 
LIMIT 1;
```

**3. Reset Password**
```
POST {{base_url}}{{api_version}}/auth/reset-password
Body:
{
  "token": "{{token_from_db}}",
  "new_password": "NuevaPassword123!"
}
```

**4. Login**
```
POST {{base_url}}{{api_version}}/auth/login
Body:
{
  "email": "usuario@example.com",
  "password": "NuevaPassword123!"
}
```

---

## Scripts de Postman

### Pre-request Script (para reset-password)

Si quieres obtener el último token automáticamente desde una variable:

```javascript
// Guardar el token desde la respuesta de forgot-password
pm.environment.set("reset_token", pm.response.json().token);
```

### Tests (para login)

Validar y guardar los tokens de autenticación:

```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has access token", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.access_token).to.exist;
    pm.environment.set("access_token", jsonData.access_token);
});

pm.test("Response has user data", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.user).to.exist;
    pm.expect(jsonData.user.email).to.exist;
});
```

---

## Obtener Token de la Base de Datos

### Opción 1: psql (línea de comandos)

```bash
docker-compose exec db psql -U postgres -d siscom_db -c \
  "SELECT token, email, expires_at AT TIME ZONE 'UTC' as expires_at, used \
   FROM tokens_confirmacion \
   WHERE type = 'password_reset' \
   ORDER BY created_at DESC \
   LIMIT 5;"
```

### Opción 2: Desde logs de Docker

```bash
docker-compose logs api | grep "PASSWORD RESET"
```

### Opción 3: Cliente SQL (DBeaver, pgAdmin, etc.)

```sql
SELECT 
    token,
    email,
    expires_at AT TIME ZONE 'UTC' as expires_at,
    used,
    created_at AT TIME ZONE 'UTC' as created_at,
    CASE 
        WHEN expires_at > NOW() THEN 'VÁLIDO'
        ELSE 'EXPIRADO'
    END as estado
FROM tokens_confirmacion
WHERE type = 'password_reset'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Validaciones de Contraseña

Las contraseñas deben cumplir con:

- ✅ Mínimo 8 caracteres
- ✅ Al menos una letra mayúscula (A-Z)
- ✅ Al menos una letra minúscula (a-z)
- ✅ Al menos un número (0-9)
- ✅ Al menos un carácter especial (!@#$%^&*(),.?":{}|<>)

### Ejemplos de Contraseñas Válidas:

- ✅ `Password123!`
- ✅ `MiClaveSegura99#`
- ✅ `NuevaPassword123!`
- ✅ `Abc12345!`

### Ejemplos de Contraseñas Inválidas:

- ❌ `pass` (muy corta)
- ❌ `password123!` (sin mayúscula)
- ❌ `PASSWORD123!` (sin minúscula)
- ❌ `Password!` (sin número)
- ❌ `Password123` (sin carácter especial)

---

## Códigos de Estado HTTP

| Código | Descripción | Cuándo ocurre |
|--------|-------------|---------------|
| 200 | OK | Operación exitosa |
| 400 | Bad Request | Token inválido, expirado o ya usado; contraseña inválida |
| 404 | Not Found | Usuario no encontrado |
| 422 | Unprocessable Entity | Error de validación en los datos de entrada |
| 500 | Internal Server Error | Error al comunicarse con Cognito |

---

## Tips para Pruebas

1. **Generar múltiples tokens:** Puedes solicitar recuperación múltiples veces. Solo el último token generado será válido si ya usaste los anteriores.

2. **Token expirado:** Los tokens expiran en 1 hora. Para probar tokens expirados, espera 1 hora o modifica manualmente `expires_at` en la BD.

3. **Logs útiles:** Revisa los logs de la API para ver los tokens generados durante el desarrollo:
   ```bash
   docker-compose logs -f api
   ```

4. **Variables de entorno:** Usa variables de Postman para facilitar las pruebas:
   - `{{base_url}}`: URL base de la API
   - `{{email}}`: Email del usuario de prueba
   - `{{reset_token}}`: Token obtenido de la BD
   - `{{new_password}}`: Nueva contraseña

5. **Colección de Postman:** Agrupa todos los endpoints de auth en una carpeta llamada "Authentication" para mejor organización.

---

## Importar a Postman

Puedes crear una colección en Postman con la siguiente estructura:

```
📁 SISCOM Admin API
  📁 Authentication
    📄 Login
    📄 Forgot Password
    📄 Reset Password
  📁 Users
  📁 Clients
  ...
```

Y configurar las variables de entorno:

```json
{
  "base_url": "http://localhost:8000",
  "api_version": "/api/v1",
  "email": "usuario@example.com",
  "password": "Password123!",
  "new_password": "NuevaPassword123!",
  "reset_token": ""
}
```

---

## Solución de Problemas

### Error: "Usuario no encontrado en Cognito"

**Causa:** El usuario existe en la BD pero no en Cognito  
**Solución:** Verificar que el usuario fue creado correctamente en Cognito durante el registro

### Error: "Token de recuperación inválido"

**Causa:** El token no existe en la BD o es incorrecto  
**Solución:** Verificar que copiaste correctamente el token de la BD o logs

### Error: "El token de recuperación ha expirado"

**Causa:** Han pasado más de 1 hora desde que se generó el token  
**Solución:** Solicitar un nuevo token con forgot-password

### Error: "Este token de recuperación ya ha sido utilizado"

**Causa:** Ya usaste ese token para cambiar la contraseña  
**Solución:** Solicitar un nuevo token si necesitas cambiar la contraseña nuevamente

---

**¡Listo para probar!** 🚀

